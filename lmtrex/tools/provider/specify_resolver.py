from lmtrex.common.lmconstants import (
    APIService, SYFTER, ServiceProvider, S2N_SCHEMA)
from lmtrex.services.api.v1.s2n_type import S2nKey, S2nOutput
from lmtrex.tools.provider.api import APIQuery
from lmtrex.tools.utils import get_traceback

# .............................................................................
class SpecifyResolverAPI(APIQuery):
    """Class to query Lifemapper portal APIs and return results"""
    PROVIDER = ServiceProvider.Specify[S2nKey.NAME]
    RES_MAP = S2N_SCHEMA.get_specify_resolver_map()
    
    # ...............................................
    def __init__(self, ident=None, resource=SYFTER.RESOLVE_RESOURCE, logger=None, is_dev=True):
        """Constructor
        
        Args:
            resource: Syftorium service to query
            ident: a Syftorium key for the specified resource.  If 
                ident is None, list using other_filters
            command: optional 'count' to query with other_filters
            other_filters: optional filters
            logger: optional logger for info and error messages.  If None, 
                prints to stdout    
        """
        base_url = SYFTER.REST_URL
        if is_dev:
            base_url = SYFTER.REST_URL_DEV
        url = '{}/{}'.format(base_url, resource)
        if ident is not None:
            url = '{}/{}'.format(url, ident)
        APIQuery.__init__(self, url, logger=logger)
        
    # ...............................................
    @classmethod
    def _standardize_record(cls, rec):
        newrec = {}
        for fldname, val in rec.items():
            # Leave out fields without value
            if val and fldname in cls.RES_MAP.keys():
                stdfld = cls.RES_MAP[fldname]
                newrec[stdfld] =  val
        return newrec
    
    # ...............................................
    @classmethod
    def _standardize_output(
            cls, output, record_format, query_term, service, provider_query=[], count_only=False, err=None):
        errmsgs = []
        stdrecs = []
        total = 0
        query_term = 'query_term={}; count_only={}'.format(query_term, count_only)
        if err is not None:
            errmsgs.append(err)
        try:
            stdrecs.append(cls._standardize_record(output))
        except Exception as e:
            msg = cls._get_error_message(err=e)
            errmsgs.append(msg)
                        
        std_output = S2nOutput(
            total, query_term, service, cls.PROVIDER, 
            provider_query=provider_query, record_format=record_format, 
            records=stdrecs, errors=errmsgs)

        return std_output

    
# ...............................................
    @classmethod
    def query_for_guid(cls, guid, logger=None):
        """Return an ARK record for a guid using the Specify resolver service.
        
        Args:
            guid: a unique identifier for a speciment record
            logger: optional logger for info and error messages.  If None, 
                prints to stdout    

        Return: 
            a dictionary containing one or more keys: 
                count, records, error, warning
            
        Example URL: 
            http://services.itis.gov/?q=nameWOInd:Spinus\%20tristis&wt=json
        """
        api = SpecifyResolverAPI(ident=guid, logger=logger)

        try:
            cls.query_by_get(output_type='json')
        except Exception as e:
            std_output = cls.get_failure(errors=[cls._get_error_message(err=e)])
        else:
            try:
                output = api.output['response']
            except:
                if api.error is not None:
                    std_output = cls.get_failure(
                        errors=[cls._get_error_message(err=api.error)])
                else:
                    std_output = cls.get_failure(
                        errors=[cls._get_error_message(
                            msg='Missing `response` element')])
            else:
                # Standardize output from provider response
                std_output = cls._standardize_output(
                    output, ITIS.COUNT_KEY, ITIS.RECORDS_KEY, ITIS.RECORD_FORMAT, 
                    sciname, APIService.Name['endpoint'], provider_query=[api.url], is_accepted=is_accepted, err=api.error)
        return std_output

    
# ...............................................

"""
solr query through API: https://dev.syftorium.org/api/v1/resolve/2facc7a2-dd88-44af-b95a-733cc27527d4
response:
{"_version_":1701562470690193418,
"dataset_guid":"University of Kansas Biodiversity Institute Fish Tissue Collection",
"id":"2facc7a2-dd88-44af-b95a-733cc27527d4",
"url":"https://notyeti-195.lifemapper.org/api/v1/sp_cache/collection/ku_fish_tissue_test_1/specimens/2facc7a2-dd88-44af-b95a-733cc27527d4",
"what":"MaterialSample",
"when":"2021-06-03",
"where":"KU",
"who":"KUIT"}

direct solr query from localhost:  http://localhost:8983/solr/spcoco/select?q=2facc7a2-dd88-44af-b95a-733cc27527d4
response:
{
  "responseHeader":{
    "status":0,
    "QTime":0,
    "params":{
      "q":"2facc7a2-dd88-44af-b95a-733cc27527d4"}},
  "response":{"numFound":1,"start":0,"numFoundExact":true,"docs":[
      {
        "id":"2facc7a2-dd88-44af-b95a-733cc27527d4",
        "dataset_guid":"University of Kansas Biodiversity Institute Fish Tissue Collection",
        "who":"KUIT",
        "what":"MaterialSample",
        "when":"2021-06-03",
        "where":"KU",
        "url":"https://notyeti-195.lifemapper.org/api/v1/sp_cache/collection/ku_fish_tissue_test_1/specimens/2facc7a2-dd88-44af-b95a-733cc27527d4",
        "_version_":1701562470690193418}]
  }}

"""