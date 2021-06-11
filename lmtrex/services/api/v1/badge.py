import cherrypy
import os

from lmtrex.common.lmconstants import (
    IMG_PATH, ServiceProvider, APIService, APIServiceNew, ICON_CONTENT)

from lmtrex.tools.utils import get_traceback

from lmtrex.services.api.v1.base import _S2nService
from lmtrex.services.api.v1.s2n_type import S2nKey

# .............................................................................
@cherrypy.expose
# @cherrypy.popargs('path_occ_id')
class BadgeSvc(_S2nService):
    SERVICE_TYPE = APIService.Badge
    PARAMETER_KEYS = APIServiceNew.Badge['params']

    # ...............................................
    def get_icon(self, provider, icon_status):
        # GBIF
        if provider == ServiceProvider.GBIF[S2nKey.PARAM]:
            fname = ServiceProvider.GBIF['icon'][icon_status]
        # iDigBio
        elif provider == ServiceProvider.iDigBio[S2nKey.PARAM]:
            fname = ServiceProvider.iDigBio['icon'][icon_status]
        # iDigBio
        elif provider == ServiceProvider.Lifemapper[S2nKey.PARAM]:
            fname = ServiceProvider.Lifemapper['icon'][icon_status]
        # MorphoSource
        elif provider == ServiceProvider.MorphoSource[S2nKey.PARAM]:
            fname = ServiceProvider.MorphoSource['icon'][icon_status]
        # Specify
        elif provider == ServiceProvider.Specify[S2nKey.PARAM]:
            fname = ServiceProvider.Specify['icon'][icon_status]
            
        full_filename = os.path.join(IMG_PATH, fname)

        return full_filename

    # ...............................................
    # ...............................................
    def GET(self, provider=None, icon_status=None, stream=True, **kwargs):
        """Get one icon to indicate a provider in a GUI
        
        Args:
            provider: string containing a comma delimited list of provider codes.  The icon 
                for only the first provider will be returned.  If the string is not present
                or 'all', the first provider in the default list of providers will be returned.
            icon_status: string indicating which version of the icon to return, valid options are:
                lmtrex.common.lmconstants.VALID_ICON_OPTIONS (active, inactive, hover) 
            stream: If true, return a generator for streaming output, else return
                file contents
            kwargs: any additional keyword arguments are ignored

        Return:
            a file containing the requested icon
        """
        try:
            usr_params, info_valid_options = self._standardize_params_new(
                provider=provider, icon_status=icon_status)
        except Exception as e:
            traceback = get_traceback()
            output = self.get_failure(query_term='provider={}, icon_status={}'.format(
                provider, icon_status), errors=[traceback])
            return output.response
        
        # Without a provider, send online status
        if len(usr_params['provider']) == 0:
            output = self._show_online(providers=valid_providers)
            return output.response

        # Only first provider is used
        provider = usr_params['provider'].pop()
        icon_status = usr_params['icon_status']
        try:
            icon_fname = self.get_icon(provider, icon_status)
        except Exception as e:
            traceback = get_traceback()
            output = self.get_failure(query_term='provider={}, icon_status={}'.format(
                provider, icon_status), errors=[traceback])
            return output.response

        # Whew
        ifile = open(icon_fname, mode='rb')
        # ret_file_name = os.path.basename(icon_fname)
        # cherrypy.response.headers[
        #     'Content-Disposition'] = 'attachment; filename="{}"'.format(ret_file_name)
        cherrypy.response.headers['Content-Type'] = ICON_CONTENT
        
        if stream:
            return cherrypy.lib.file_generator(ifile)
        else:
            icontent = ifile.read()
            ifile.close()
            return icontent
    

# .............................................................................
if __name__ == '__main__':
    svc = BadgeSvc()
    # Get all providers
    valid_providers = svc.get_valid_providers()
    retval = svc.GET(provider='gbif', icon_status='activex')
    # for pr in valid_providers:
    #     for stat in VALID_ICON_OPTIONS:
    #         retval = svc.GET(provider=pr, icon_status=stat)
    #         print(retval)
    