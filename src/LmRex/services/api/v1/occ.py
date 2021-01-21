import cherrypy

from LmRex.common.lmconstants import ServiceProvider, APIService
from LmRex.tools.api import (
    GbifAPI, IdigbioAPI, MorphoSourceAPI, SpecifyPortalAPI, BisonAPI)
from LmRex.services.api.v1.base import _S2nService
from LmRex.services.api.v1.resolve import SpecifyResolve
from LmRex.services.api.v1.dataset import DatasetGBIF
        
# .............................................................................
@cherrypy.expose
class _OccurrenceSvc(_S2nService):
    SERVICE_TYPE = APIService.Occurrence
    
# .............................................................................
@cherrypy.expose
class OccGBIF(_OccurrenceSvc):
    PROVIDER = ServiceProvider.GBIF
    # ...............................................
    def get_records(self, occid, count_only):
        output = GbifAPI.get_occurrences_by_occid(
            occid, count_only=count_only)
        output['service'] = self.SERVICE_TYPE
        output['provider'] = self.PROVIDER['name']
        return output

    # ...............................................
    @cherrypy.tools.json_out()
    def GET(self, occid=None, count_only=None, **kwargs):
        usr_params = self._standardize_params(occid=occid, count_only=count_only)
        occurrence_id = usr_params['occid']
        if occurrence_id is None:
            return self._show_online()
        else:
            return self.get_records(occurrence_id, usr_params['count_only'])


# .............................................................................
@cherrypy.expose
class OccIDB(_OccurrenceSvc):
    PROVIDER = ServiceProvider.iDigBio
    # ...............................................
    def get_records(self, occid, count_only):
        output = IdigbioAPI.get_occurrences_by_occid(occid, count_only=count_only)
        output['service'] = self.SERVICE_TYPE
        output['provider'] = self.PROVIDER['name']
        return output

    # ...............................................
    @cherrypy.tools.json_out()
    def GET(self, occid=None, count_only=None, **kwargs):
        usr_params = self._standardize_params(occid=occid, count_only=count_only)
        occurrence_id = usr_params['occid']
        if occurrence_id is None:
            return self._show_online()
        else:
            return self.get_records(occurrence_id, usr_params['count_only'])
          
# .............................................................................
@cherrypy.expose
class OccMopho(_OccurrenceSvc):
    PROVIDER = ServiceProvider.MorphoSource
    # ...............................................
    def get_records(self, occid, count_only):
        output = MorphoSourceAPI.get_occurrences_page1_by_occid(
            occid, count_only=count_only)
        output['service'] = self.SERVICE_TYPE
        output['provider'] = self.PROVIDER['name']
        return output

    # ...............................................
    @cherrypy.tools.json_out()
    def GET(self, occid=None, count_only=None, **kwargs):
        usr_params = self._standardize_params(occid=occid, count_only=count_only)
        occurrence_id = usr_params['occid']
        if occurrence_id is None:
            return self._show_online()
        else:
            return self.get_records(occurrence_id, usr_params['count_only'])

# .............................................................................
@cherrypy.expose
class OccSpecify(_OccurrenceSvc):
    PROVIDER = ServiceProvider.Specify
    # ...............................................
    def get_records(self, url, occid):
        msg = 'Spocc failed: url = {}, occid = {}'.format(url, occid)
        if url is None:
            if occid is None:
                output = {'info': 'S^n service is online'}
            else:
                # Specify ARK Record
                spark = SpecifyResolve()
                solr_output = spark.get_specify_guid_meta(occid)
                # Specify Record from URL in ARK
                (url, msg) = spark.get_url_from_meta(solr_output)
                
        if url is not None:
            output = SpecifyPortalAPI.get_specify_record(url)
        else:
            output = {'info': msg}
        output['service'] = self.SERVICE_TYPE
        output['provider'] = self.PROVIDER['name']
        return output 
    
    # ...............................................
    @cherrypy.tools.json_out()
    def GET(self, occid=None, url=None, **kwargs):
        usr_params = self._standardize_params(occid=occid, url=url)
        if usr_params['url'] is None and usr_params['occid'] is None:
            return self._show_online()
        else:
            return self.get_records(usr_params['url'], usr_params['occid'])

# .............................................................................
@cherrypy.expose
class OccTentacles(_OccurrenceSvc):
    
    # ...............................................
    def get_records(self, usr_params):
        all_output = {}
        all_count = 0
        
        occid = usr_params['occid']
        count_only = usr_params['count_only']
        
        # Specify ARK Record
        spark = SpecifyResolve()
        solr_output = spark.get_specify_guid_meta(occid)
        try:
            all_count += solr_output['count']
        except:
            pass
        # Do not add GUID service record to occurrence records
        # all_output[ServiceProvider.Specify['name']] = solr_output
        
        # Specify Record from URL in ARK
        (url, msg) = spark.get_url_from_meta(solr_output)
        if url is not None:
            spocc = OccSpecify()
            sp_output = spocc.get_records(url, occid)
            try:
                all_count += sp_output['count']
            except:
                pass
        else:
            sp_output = {'error': msg}
        all_output[ServiceProvider.Specify['name']] = sp_output
        
        # GBIF copy/s of Specify Record
        gocc = OccGBIF()
        gbif_output = gocc.get_records(occid, count_only)
        try:
            all_count += gbif_output['count']
        except:
            pass
        all_output['GBIF Records'] = gbif_output
        
        # iDigBio copy/s of Specify Record
        idbocc = OccIDB()
        idb_output = idbocc.get_records(occid, count_only)
        try:
            all_count += idb_output['count']
        except:
            pass
        all_output['iDigBio Records'] = idb_output
        
        # MorphoSource records connected to Specify Record
        mopho = OccMopho()
        mopho_output = mopho.get_records(occid, count_only)
        try:
            all_count += mopho_output['count']
        except:
            pass
        all_output['MorphoSource Records'] = mopho_output
        return all_output

    # ...............................................
    # ...............................................
    @cherrypy.tools.json_out()
    def GET(self, occid=None, count_only=None, **kwargs):
        usr_params = self._standardize_params(occid=occid, count_only=count_only)
        return self.get_records(usr_params)
        
# .............................................................................
if __name__ == '__main__':
    # test
    from LmRex.common.lmconstants import TST_VALUES   
    
    gocc = DatasetGBIF()
    gout = gocc.GET(TST_VALUES.FISH_DS_GUIDS[0], count_only=True)
    print(gout) 

    for occid in TST_VALUES.BIRD_OCC_GUIDS[:1]:
        print(occid)
        # Queries Specify without ARK URL
        spocc = OccSpecify()
        sp_output = spocc.GET(url=None, occid=occid, count_only=False)
        for k, v in sp_output.items():
            print('  {}: {}'.format(k, v))

        # Queries all services
        s2napi = OccTentacles()
        all_output = s2napi.GET(occid=occid, count_only=False)
        
        for svc, one_output in all_output.items():
            print('  {}'.format(svc))
            for k, v in one_output.items():
                print('  {}: {}'.format(k, v))
            print('')

