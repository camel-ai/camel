# ZoomInfo Toolkit for CAMEL-AI

A comprehensive ZoomInfo API integration for the CAMEL-AI framework, enabling B2B data intelligence, company research, and contact discovery capabilities.

## 🚀 Features

- **Company Search**: Search for companies using various parameters (name, industry, size, etc.)
- **Contact Search**: Find contacts by company, job title, management level, and more
- **Contact Enrichment**: Enrich existing contact data with additional information
- **JWT Authentication**: Secure token-based authentication with automatic refresh
- **Error Handling**: Comprehensive error handling and retry mechanisms
- **MCP Support**: Full Model Context Protocol integration

## 📋 Requirements

- Python 3.8+
- ZoomInfo API credentials (username/password or PKI)
- Required packages listed in `requirements.txt`

## 🔧 Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

### 3. Configure ZoomInfo Credentials
```bash
# Option 1: Username/Password Authentication
export ZOOMINFO_USERNAME="your_username"
export ZOOMINFO_PASSWORD="your_password"

# Option 2: PKI Authentication (Recommended for Production)
export ZOOMINFO_USERNAME="your_username"
export ZOOMINFO_CLIENT_ID="your_client_id"
export ZOOMINFO_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
Your private key content
-----END PRIVATE KEY-----"
```

## 🎯 Quick Start

### Basic Usage
```python
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ZoomInfoToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize ZoomInfo toolkit
zoominfo_toolkit = ZoomInfoToolkit()

# Create AI agent with ZoomInfo tools
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

agent = ChatAgent(
    system_message="You are a B2B intelligence assistant. Use ZoomInfo to research companies and find contacts.",
    model=model,
    tools=zoominfo_toolkit.get_tools(),
)

# Search for companies
response = agent.step("Find technology companies in California with more than 100 employees")
print(response.msg.content)
```

### Advanced Examples

#### Company Research
```python
# Search companies with specific criteria
response = agent.step(
    "Search for SaaS companies in New York with 50-500 employees, "
    "sorted by revenue in descending order."
)
```

#### Contact Discovery
```python
# Find specific roles at companies
response = agent.step(
    "Find VPs of Engineering and CTOs at fintech companies in San Francisco."
)
```

#### Data Enrichment
```python
# Enrich existing contact data
response = agent.step(
    "Enrich contact information for john@example.com and jane@techcorp.com. "
    "Return their full name, job title, company, and contact accuracy score."
)
```

## 📚 API Reference

### search_companies()
Search for companies using ZoomInfo's company search API.

**Parameters:**
- `company_name` (str, optional): Company name to search for
- `company_website` (str, optional): Company website URL
- `industry` (str, optional): Industry or sector to filter by
- `rpp` (int, default=10): Results per page (1-100)
- `page` (int, default=1): Page number for pagination
- `sort_by` (str, default="name"): Sort field ("name", "employeeCount", "revenue")
- `sort_order` (str, default="asc"): Sort order ("asc" or "desc")

**Returns:**
```python
{
    "maxResults": 10,
    "totalResults": 150,
    "currentPage": 1,
    "data": [
        {
            "id": 12345,
            "name": "Example Corp"
        }
    ]
}
```

### search_contacts()
Search for contacts using ZoomInfo's contact search API.

**Parameters:**
- `company_name` (str, optional): Company name to search in
- `job_title` (str, optional): Job title to search for
- `management_level` (str, optional): Management level filter
- `email_address` (str, optional): Email address to search for
- `rpp` (int, default=10): Results per page
- `page` (int, default=1): Page number
- `sort_by` (str, default="contactAccuracyScore"): Sort field
- `sort_order` (str, default="desc"): Sort order

**Returns:**
```python
{
    "maxResults": 10,
    "totalResults": 50,
    "currentPage": 1,
    "data": [
        {
            "id": 67890,
            "firstName": "John",
            "lastName": "Doe",
            "jobTitle": "Software Engineer",
            "contactAccuracyScore": 95,
            "hasEmail": true,
            "hasDirectPhone": true,
            "company": {
                "id": 12345,
                "name": "Example Corp"
            }
        }
    ]
}
```

### enrich_contact()
Enrich existing contact information with additional data.

**Parameters:**
- `match_person_input` (List[Dict]): List of contact inputs to match
- `output_fields` (List[str]): Fields to return in enriched data

**Returns:**
```python
{
    "success": true,
    "data": {
        "outputFields": ["id", "firstName", "lastName", "email"],
        "result": [
            {
                "input": {"emailAddress": "john@example.com"},
                "data": [
                    {
                        "id": 67890,
                        "firstName": "John",
                        "lastName": "Doe",
                        "email": "john.doe@company.com"
                    }
                ],
                "matchStatus": "matched"
            }
        ]
    }
}
```

## 🧪 Testing

Run the test suite:
```bash
# Install test dependencies
pip install pytest pytest-mock

# Run tests
pytest test/toolkits/test_zoominfo_toolkit.py -v
```

## 📖 Examples

Check the `examples/toolkits/zoominfo_toolkit.py` file for comprehensive usage examples including:
- Company research scenarios
- Contact discovery workflows
- Market research applications
- Sales prospecting examples

## 🔐 Authentication

### Username/Password Authentication
Simple and straightforward, suitable for development and testing.

### PKI Authentication (Recommended)
More secure for production environments:
1. Generate a private/public key pair
2. Register your public key with ZoomInfo
3. Use your private key for JWT token generation

## 🚨 Error Handling

The toolkit includes comprehensive error handling:
- **Network errors**: Automatic retry with exponential backoff
- **Authentication errors**: Automatic token refresh
- **API errors**: Detailed error messages and suggestions
- **Rate limiting**: Respectful request timing

## 📊 Data Quality

ZoomInfo provides data quality indicators:
- **Contact Accuracy Score**: 0-100 scale for contact reliability
- **Field Availability**: Boolean flags for available data fields
- **Last Updated**: Timestamps for data freshness

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## 🔗 Links

- [ZoomInfo API Documentation](https://api-docs.zoominfo.com/)
- [CAMEL-AI Framework](https://github.com/camel-ai/camel)
- [ZoomInfo Developer Portal](https://developer.zoominfo.com/)

## 🆘 Support

For issues and questions:
1. Check the [troubleshooting guide](TROUBLESHOOTING.md)
2. Review [common issues](COMMON_ISSUES.md)
3. Open a GitHub issue with detailed information

## 📈 Performance Tips

- **Batch requests**: Use larger `rpp` values for efficiency
- **Selective fields**: Request only necessary output fields
- **Caching**: Cache frequently accessed company data
- **Rate limiting**: Implement client-side rate limiting

---

**Note**: This toolkit is designed for B2B intelligence and sales/marketing use cases. Please ensure compliance with data privacy regulations and ZoomInfo's terms of service.
