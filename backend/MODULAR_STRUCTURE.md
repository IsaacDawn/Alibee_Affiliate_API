# Alibee Affiliator API - Modular Structure

## Overview
The Alibee Affiliator API has been refactored into a modular structure to improve maintainability, scalability, and separation of concerns. This document describes the new architecture and how to work with it.

## Directory Structure

```
backend/
├── app.py                 # Main FastAPI application
├── app_backup.py          # Backup of original monolithic app.py
├── app_new.py             # New modular app.py (temporary)
├── config/                # Configuration module
│   ├── __init__.py
│   └── settings.py        # Application settings and configuration
├── models/                # Data models and schemas
│   ├── __init__.py
│   └── schemas.py         # Pydantic models
├── database/              # Database operations
│   ├── __init__.py
│   └── connection.py      # Database connection and operations
├── services/              # External service integrations
│   ├── __init__.py
│   └── aliexpress.py      # AliExpress API client
├── routes/                # API route handlers
│   ├── __init__.py
│   ├── health.py          # Health check endpoints
│   ├── products.py        # Product management endpoints
│   ├── search.py          # Search endpoints
│   ├── categories.py      # Category endpoints
│   └── stats.py           # Statistics endpoints
└── utils/                 # Utility functions
    ├── __init__.py
    └── helpers.py         # Helper functions and utilities
```

## Module Descriptions

### 1. Config Module (`config/`)
**Purpose**: Centralized configuration management
- **settings.py**: Contains all application settings, database configuration, API keys, and environment variables
- **Benefits**: Easy configuration management, environment-specific settings, centralized API configuration

### 2. Models Module (`models/`)
**Purpose**: Data models and validation schemas
- **schemas.py**: Pydantic models for request/response validation
- **Benefits**: Type safety, automatic validation, clear data contracts

### 3. Database Module (`database/`)
**Purpose**: Database operations and connection management
- **connection.py**: Database connection, CRUD operations, and query management
- **Benefits**: Centralized database logic, connection pooling, error handling

### 4. Services Module (`services/`)
**Purpose**: External service integrations
- **aliexpress.py**: AliExpress API client with authentication and request handling
- **Benefits**: Isolated external dependencies, easy testing, service abstraction

### 5. Routes Module (`routes/`)
**Purpose**: API endpoint definitions and handlers
- **health.py**: Health check and status endpoints
- **products.py**: Product management (save, unsave, update)
- **search.py**: Product search and filtering
- **categories.py**: Category management
- **stats.py**: Application statistics
- **Benefits**: Organized endpoints, clear separation of concerns, easy maintenance

### 6. Utils Module (`utils/`)
**Purpose**: Utility functions and helpers
- **helpers.py**: Common utility functions, formatting, validation
- **Benefits**: Reusable code, consistent formatting, centralized utilities

## Key Benefits

### 1. **Separation of Concerns**
- Each module has a single responsibility
- Changes in one module don't affect others
- Clear boundaries between different functionalities

### 2. **Maintainability**
- Easy to locate and modify specific functionality
- Reduced code duplication
- Clear module dependencies

### 3. **Scalability**
- Easy to add new features without affecting existing code
- Modular testing approach
- Independent deployment of modules

### 4. **Testing**
- Each module can be tested independently
- Mock external dependencies easily
- Unit tests for specific functionality

### 5. **Code Reusability**
- Common functionality in utils module
- Shared models across different routes
- Centralized configuration

## Migration from Monolithic Structure

### Before (Monolithic)
```python
# All code in single app.py file (2800+ lines)
# Mixed concerns: routes, database, API calls, utilities
# Hard to maintain and test
```

### After (Modular)
```python
# Clean separation of concerns
# Each module handles specific functionality
# Easy to maintain and extend
```

## Usage Examples

### Adding a New Endpoint
1. Create route in appropriate module (`routes/`)
2. Add any new models to `models/schemas.py`
3. Add database operations to `database/connection.py` if needed
4. Import and include in `routes/__init__.py`

### Adding a New Service
1. Create new service file in `services/`
2. Add configuration to `config/settings.py`
3. Import and use in routes as needed

### Modifying Database Operations
1. Update `database/connection.py`
2. Add new models to `models/schemas.py` if needed
3. Update routes that use the modified operations

## Configuration

### Environment Variables
All configuration is managed through environment variables in `config/settings.py`:

```python
# Database
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=alibee_affiliate

# AliExpress API
APP_KEY=your_app_key
APP_SECRET=your_app_secret

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Testing

### Running the Application
```bash
cd backend
python -m uvicorn app:app --reload --port 8080
```

### Testing Endpoints
```bash
# Health check
curl http://localhost:8080/health

# Get categories
curl http://localhost:8080/categories

# Get stats
curl http://localhost:8080/stats
```

## Best Practices

### 1. **Module Imports**
- Always use relative imports within modules
- Import only what you need
- Avoid circular imports

### 2. **Error Handling**
- Use consistent error responses
- Handle errors at appropriate levels
- Log errors for debugging

### 3. **Configuration**
- Use environment variables for sensitive data
- Provide sensible defaults
- Validate configuration on startup

### 4. **Database Operations**
- Use context managers for connections
- Handle database errors gracefully
- Use transactions for multi-step operations

### 5. **API Design**
- Use consistent response formats
- Validate input data
- Provide clear error messages

## Future Enhancements

### 1. **Caching**
- Add Redis for caching frequently accessed data
- Cache AliExpress API responses
- Cache database queries

### 2. **Authentication**
- Add JWT-based authentication
- Role-based access control
- API key management

### 3. **Monitoring**
- Add logging framework
- Performance monitoring
- Health checks for dependencies

### 4. **Testing**
- Unit tests for each module
- Integration tests
- API endpoint tests

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Check `__init__.py` files
   - Verify module paths
   - Check Python path

2. **Database Connection Issues**
   - Verify database configuration
   - Check database server status
   - Validate credentials

3. **API Configuration Issues**
   - Check environment variables
   - Verify API keys
   - Test API connectivity

### Debug Mode
Enable debug mode by setting environment variable:
```bash
export DEBUG=true
```

## Conclusion

The modular structure provides a solid foundation for the Alibee Affiliator API. It improves code organization, maintainability, and scalability while maintaining backward compatibility with existing functionality.

For questions or issues, refer to the individual module documentation or contact the development team.
