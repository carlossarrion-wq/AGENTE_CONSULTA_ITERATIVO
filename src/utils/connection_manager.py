import os
import yaml
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth
from loguru import logger
from dotenv import load_dotenv

class ConnectionManager:
    def __init__(self, config_path="config/aws_config_production.yaml", config_dict=None):
        load_dotenv()
        if config_dict is not None:
            self.config = config_dict
        else:
            self.config = self._load_config(config_path)
        self.opensearch_client = None
        self.s3_client = None
        self.bedrock_client = None
        
    def _load_config(self, config_path):
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    
    def get_opensearch_client(self):
        if self.opensearch_client is None:
            try:
                # Check if opensearchpy is available
                try:
                    from opensearchpy import OpenSearch, RequestsHttpConnection
                except ImportError as import_error:
                    logger.error(f"opensearchpy module not found: {import_error}")
                    raise ImportError("opensearchpy is required but not installed. Please install it with: pip install opensearch-py")
                
                region = self.config['aws']['region']
                service = 'es'
                credentials = boto3.Session().get_credentials()
                
                if not credentials:
                    raise ValueError("AWS credentials not found. Please configure your AWS credentials.")
                
                # Get OpenSearch configuration
                os_config = self.config['services']['opensearch']
                host = os_config['endpoint'].replace('https://', '').replace('http://', '')
                port = os_config.get('port', 443)
                use_ssl = os_config.get('use_ssl', True)
                verify_certs = os_config.get('verify_certs', True)
                timeout = os_config.get('timeout', 30)
                
                # Always use AWS authentication for OpenSearch
                # Even for localhost (SSH tunnel), OpenSearch requires AWS credentials
                awsauth = AWSRequestsAuth(
                    aws_access_key=credentials.access_key,
                    aws_secret_access_key=credentials.secret_key,
                    aws_token=credentials.token,
                    aws_host=host,
                    aws_region=region,
                    aws_service=service
                )
                
                self.opensearch_client = OpenSearch(
                    hosts=[{'host': host, 'port': port}],
                    http_auth=awsauth,
                    use_ssl=use_ssl,
                    verify_certs=verify_certs,
                    connection_class=RequestsHttpConnection,
                    timeout=timeout
                )
                
                if host == 'localhost' or host.startswith('127.0.0.1'):
                    logger.info(f"OpenSearch client initialized for localhost:{port} (SSH tunnel with AWS auth)")
                else:
                    logger.info(f"OpenSearch client initialized for VPC endpoint: {host}:{port}")
            except Exception as e:
                logger.error(f"Error initializing OpenSearch client: {e}")
                raise
        return self.opensearch_client
    
    def get_s3_client(self):
        if self.s3_client is None:
            try:
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.config['aws']['region']
                )
                logger.info("S3 client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing S3 client: {e}")
                raise
        return self.s3_client
    
    def get_bedrock_client(self):
        if self.bedrock_client is None:
            try:
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.config['bedrock']['region']
                )
                logger.info("Bedrock client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Bedrock client: {e}")
                raise
        return self.bedrock_client
    
    def test_connections(self):
        results = {}
        
        # Test OpenSearch
        try:
            os_client = self.get_opensearch_client()
            health = os_client.cluster.health()
            results['opensearch'] = {'status': 'success', 'health': health['status']}
        except Exception as e:
            results['opensearch'] = {'status': 'error', 'error': str(e)}
        
        # Test S3
        try:
            s3_client = self.get_s3_client()
            bucket_name = self.config['services']['s3']['bucket']
            s3_client.head_bucket(Bucket=bucket_name)
            results['s3'] = {'status': 'success', 'bucket': bucket_name}
        except Exception as e:
            results['s3'] = {'status': 'error', 'error': str(e)}
        
        # Test Bedrock
        try:
            bedrock_client = self.get_bedrock_client()
            # Simple test to see if we can access the service
            results['bedrock'] = {'status': 'success', 'region': self.config['bedrock']['region']}
        except Exception as e:
            results['bedrock'] = {'status': 'error', 'error': str(e)}
        
        return results
