"""Custom middleware for the tickets app."""
import mimetypes


class MimeTypeMiddleware:
    """Middleware to ensure correct MIME types for static files."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Set correct MIME types
        mimetypes.add_type('text/css', '.css')
        mimetypes.add_type('application/javascript', '.js')
        mimetypes.add_type('application/javascript', '.mjs')
        mimetypes.add_type('font/woff', '.woff')
        mimetypes.add_type('font/woff2', '.woff2')
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Fix MIME type for static files
        if request.path.startswith('/static/'):
            if request.path.endswith('.css'):
                response['Content-Type'] = 'text/css'
            elif request.path.endswith(('.js', '.mjs')):
                response['Content-Type'] = 'application/javascript'
            elif request.path.endswith('.woff'):
                response['Content-Type'] = 'font/woff'
            elif request.path.endswith('.woff2'):
                response['Content-Type'] = 'font/woff2'
                
        return response