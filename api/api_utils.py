import settings
from piston.utils import rc
import traceback
from models import ApiKey
from piston.emitters import Emitter
from piston.handler import typemapper


def build_error_response(e, request):
    
    content = {"error": True,
               "type": e.type,
               "status_code": e.status_code,
               "explanation": ""}
    content.update(e.extra)
    response = rc.BAD_REQUEST
    format = request.GET.get("format", "json")
    
    em_info = Emitter.get(format)
    RequestEmitter = em_info[0]
    emitter = RequestEmitter(content, typemapper, "", "", False)
    response.content = emitter.render(request)
    response['Content-Type'] = em_info[1]

    return response
    

class ReturnError(Exception):
    def __init__(self, status_code, type, extra):
        self.status_code = status_code
        self.type = type
        self.extra = extra

def build_unexpected(e, request):
    debug = traceback.format_exc() if settings.DEBUG else str(e)
    #TODO: logger
    return build_error_response(ReturnError(500,
                                            "InternalError",
                                            {"explanation":
                                             "An internal Freesound error ocurred.",
                                             "really_really_sorry": True,
                                             "debug": debug}
                                             ), request)

def build_invalid_url(e):
    format = e.GET.get("format", "json")
    return build_error_response(ReturnError(404,
                                            "InvalidUrl",
                                            {"explanation":
                                             "The introduced url is invalid.",}
                                             ), e) # TODO:!!!


class auth():

    def __init__(self, get_parameter='api_key'): # FROM FREESOUND
        self.get_parameter = get_parameter

    def __call__(self, f):
        """
        If there are decorator arguments, __call__() is only called
        once, as part of the decoration process! You can only give
        it a single argument, which is the function object.
        """
        def decorated_api_func(handler, request, *args, **kargs):
            try:

                # Try to get the api key
                api_key = request.GET.get(self.get_parameter, False)
                if not api_key:
                    raise ReturnError(401, "AuthenticationError",
                                          {"explanation":  "Please include your api key as the api_key GET parameter"},
                                          )
                try:
                    db_api_key = ApiKey.objects.get(key=api_key, status='OK')
                except ApiKey.DoesNotExist:
                    raise ReturnError(401, "AuthenticationError",
                                          {"explanation":  "Supplied api_key does not exist"},
                                          )

                request.user = db_api_key.user
                return f(handler, request, *args, **kargs)
            except ReturnError, e:
                return build_error_response(e, request)
            except Exception, e:
                return build_unexpected(e, request)

        return decorated_api_func



