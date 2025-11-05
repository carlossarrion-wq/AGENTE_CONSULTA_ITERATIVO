# SSH Tunnel to OpenSearch - Diagnostic Report

## Error Summary
```
Port 9201 opened for sessionId carlos.sarrion@es.ibm.com-brf3yqecoiy2oxhhrh2cjsoqu4.
Waiting for connections...
Connection accepted for session [carlos.sarrion@es.ibm.com-brf3yqecoiy2oxhhrh2cjsoqu4]
Connection to destination port failed, check SSM Agent logs.
```

## Root Cause
The SSH tunnel establishes successfully, but the EC2 instance **cannot connect to the OpenSearch domain** on port 443. Testing from the EC2 instance shows:
- ✅ DNS resolution works: `vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com` → `10.0.3.156`
- ❌ Connection refused: `curl: (7) Failed to connect to vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com port 443`

## Infrastructure Analysis

### Network Configuration
- **VPC**: vpc-04ba39cd0772a280b
- **EC2 Instance**: i-0aed93266a5823099
  - Subnet: subnet-0e984b3f275d482f1 (10.0.1.0/24, eu-west-1a)
  - Security Group: sg-0224a833831bb893a
- **OpenSearch Domain**: rag-opensearch-clean
  - Subnet: subnet-09d9eef6deec49835 (10.0.3.0/24, eu-west-1a)
  - Security Group: sg-08fea11c4a73ef52f
  - Private IP: 10.0.3.156

### Security Groups
✅ **EC2 Security Group (sg-0224a833831bb893a)**
- Egress: Allow all traffic to 0.0.0.0/0

✅ **OpenSearch Security Group (sg-08fea11c4a73ef52f)**
- Ingress: Allow TCP 443 from sg-0224a833831bb893a (EC2 security group)

### Network ACLs
✅ Allow all traffic (rule 100)

### OpenSearch Access Policy
✅ Allows IAM role: `arn:aws:iam::701055077130:role/rag-system-production-RAGEC2Role-hawdzi5Lrv3d`

## Possible Causes

### 1. OpenSearch Domain State Issue
The domain might be in a degraded or unhealthy state even though AWS reports it as "active".

### 2. ENI (Elastic Network Interface) Issue
The network interface for OpenSearch might not be properly attached or configured.

### 3. OpenSearch Service Not Listening
The OpenSearch service might not be running or listening on port 443.

## Solutions

### Solution 1: Check OpenSearch Domain Health
```bash
# Check cluster health through AWS API
aws opensearch describe-domain \
  --domain-name rag-opensearch-clean \
  --region eu-west-1 \
  --query 'DomainStatus.[DomainId,Processing,Deleted,EngineVersion]'

# Check if there are any service software updates pending
aws opensearch describe-domain \
  --domain-name rag-opensearch-clean \
  --region eu-west-1 \
  --query 'DomainStatus.ServiceSoftwareOptions'
```

### Solution 2: Verify ENI Configuration
```bash
# Find the ENI associated with OpenSearch
aws ec2 describe-network-interfaces \
  --filters "Name=subnet-id,Values=subnet-09d9eef6deec49835" \
  --region eu-west-1 \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status,PrivateIpAddress,Groups[*].GroupId]'
```

### Solution 3: Test Direct Connection from EC2
```bash
# SSH into EC2 and test
aws ssm start-session --target i-0aed93266a5823099 --region eu-west-1

# Once in the session:
# Test DNS
nslookup vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com

# Test connectivity
telnet 10.0.3.156 443

# Test with curl (with AWS auth)
curl -k https://vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com/_cluster/health
```

### Solution 4: Restart OpenSearch Domain
If the domain is in a bad state, you might need to modify it to trigger a restart:

```bash
# This will trigger a blue/green deployment
aws opensearch update-domain-config \
  --domain-name rag-opensearch-clean \
  --region eu-west-1 \
  --cluster-config InstanceType=t3.small.search,InstanceCount=1
```

⚠️ **Warning**: This will cause downtime during the update.

### Solution 5: Alternative - Use Public Endpoint
If the VPC endpoint continues to have issues, consider temporarily using a public endpoint:

1. Modify OpenSearch domain to add public access
2. Update security to allow your IP
3. Connect directly without SSH tunnel

### Solution 6: Check CloudWatch Logs
```bash
# Check OpenSearch logs for errors
aws logs tail /aws/opensearch/domains/rag-opensearch-clean/application-logs \
  --region eu-west-1 \
  --follow
```

## Recommended Immediate Actions

1. **Check ENI Status**
   ```bash
   aws ec2 describe-network-interfaces \
     --filters "Name=private-ip-address,Values=10.0.3.156" \
     --region eu-west-1
   ```

2. **Verify OpenSearch is Healthy**
   ```bash
   aws opensearch describe-domain \
     --domain-name rag-opensearch-clean \
     --region eu-west-1 \
     --output json > opensearch_status.json
   ```

3. **Check for Recent Changes**
   ```bash
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=ResourceName,AttributeValue=rag-opensearch-clean \
     --region eu-west-1 \
     --max-results 20
   ```

## Workaround: Direct EC2 Access

If the SSH tunnel continues to fail, you can run the ingestion scripts directly on the EC2 instance:

```bash
# 1. Copy your code to EC2
aws s3 cp --recursive . s3://your-bucket/code/
aws ssm start-session --target i-0aed93266a5823099 --region eu-west-1

# 2. On EC2, download and run
aws s3 cp --recursive s3://your-bucket/code/ /home/ec2-user/code/
cd /home/ec2-user/code
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

# 3. Update config to use VPC endpoint directly
# Edit config/multi_app_ingestion_config.yaml:
# opensearch:
#   endpoint: "vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com"
#   port: 443

# 4. Run ingestion
python3 src/utils/multi_app_aws_ingestion_manager_with_summarization.py --app saplcorp
```

## Next Steps

1. Run the ENI check command to see if the network interface is healthy
2. Check CloudWatch logs for OpenSearch errors
3. Consider opening an AWS support case if the issue persists
4. As a temporary workaround, run scripts directly on EC2 instance

## Contact AWS Support

If none of these solutions work, open an AWS support case with:
- Domain name: rag-opensearch-clean
- Error: "Connection refused on port 443 from VPC"
- Include the diagnostic output from this document
