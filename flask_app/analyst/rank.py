"""Class for the Specify Network Name API service."""
from http import HTTPStatus
from werkzeug.exceptions import BadRequest

from flask_app.common.s2n_type import APIService, AnalystOutput
from flask_app.analyst.base import _AnalystService

from sppy.aws.aws_constants import PROJ_BUCKET
from sppy.tools.provider.awss3 import S3Query
from sppy.tools.s2n.utils import (combine_errinfo, get_traceback)


# .............................................................................
class RankSvc(_AnalystService):
    """Specify Network API service for retrieving taxonomic information."""
    SERVICE_TYPE = APIService.Rank
    ORDERED_FIELDNAMES = []

    # ...............................................
    @classmethod
    def rank_counts(cls, by_species, descending=True, limit=1, format="JSON"):
        """Return occurrence and species counts for dataset/organization identifiers.

        Args:
            by_species: boolean URL parameter indicating whether to rank datasets by
                species count (True) or occurrence count (False).
            descending: boolean URL parameter indicating whether to rank top down (True)
                or bottom up (False).
            limit: integer URL parameter specifying the number of ordered records to
                return.
            format: output format, options "CSV" or "JSON"

            full_output (flask_app.common.s2n_type.AnalystOutput): including records
                as a list of lists (CSV) or dictionaries (JSON) of records
                containing dataset_key,  occurrence count, and species count.
        """
        if by_species is None:
            return cls.get_endpoint()

        records = []
        try:
            good_params, errinfo = cls._standardize_params(
                by_species=by_species, descending=descending, limit=limit)

        except BadRequest as e:
            errinfo = {"error": e.description}

        else:
            # Query for ordered dataset counts
            try:
                records, errors = cls._get_ordered_counts(
                    good_params["by_species"], good_params["descending"],
                    good_params["limit"], format)
            except Exception:
                errors = {"error": get_traceback()}

            # Combine errors from success or failure
            errinfo = combine_errinfo(errinfo, errors)

        # Assemble
        full_out = AnalystOutput(
            cls.SERVICE_TYPE["name"], description=cls.SERVICE_TYPE["description"],
            records=records, errors=errinfo)

        return full_out.response

    # ...............................................
    @classmethod
    def _get_ordered_counts(cls, by_species, descending, limit, format):
        records = []
        s3 = S3Query(PROJ_BUCKET)
        try:
            records, errinfo = s3.rank_datasets(
                by_species, descending=descending, limit=limit)

        except Exception:
            errinfo = {"error": get_traceback()}

        return records, errinfo

# .............................................................................
if __name__ == "__main__":
    format = "CSV"
    dataset_key = "0000e36f-d0e9-46b0-aa23-cc1980f00515"

    svc = RankSvc()
    response = svc.get_endpoint()
    AnalystOutput.print_output(response, do_print_rec=True)
    # print(response)
    by_species = True
    descending = True
    limit = 5
    response = svc.rank_counts(
        by_species, descending=descending, limit=limit, format=format)
    AnalystOutput.print_output(response, do_print_rec=True)
    # print(response)

