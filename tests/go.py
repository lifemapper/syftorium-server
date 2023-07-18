import zipfile

import base64
import boto3
import csv
import datetime
import io
import logging
from logging.handlers import RotatingFileHandler
import os
import pandas
import requests
import subprocess

# --------------------------------------------------------------------------------------
# Constants for GBIF data, local dev machine, EC2, S3
# --------------------------------------------------------------------------------------
GBIF_BASE_URL = "https://api.gbif.org/v1/occurrence/download/request/"
ZIP_EXT = ".zip"
GBIF_OCC_FNAME = "occurrence.txt"
FIELD_SUBSET = [
    "gbifID",
    "datasetKey",
    "occurrenceID",
    "date",
    "locality",
    "countryCode",
    "stateProvince",
    "acceptedScientificName",
    "vernacularName",
    "taxonRank",
    "taxonomicStatus",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    ]

# Log processing progress
LOGINTERVAL = 1000000
LOG_FORMAT = " ".join(["%(asctime)s", "%(levelname)-8s", "%(message)s"])
LOG_DATE_FORMAT = "%d %b %Y %H:%M"
LOGFILE_MAX_BYTES = 52000000
LOGFILE_BACKUP_COUNT = 5


# ----------------------------------------------------
def get_logger(log_directory, log_name, log_level=logging.INFO):
    filename = f"{log_name}.log"
    if log_directory is not None:
        filename = os.path.join(log_directory, f"{filename}")
        os.makedirs(log_directory, exist_ok=True)
    # create file handler
    handler = RotatingFileHandler(
        filename, mode="w", maxBytes=LOGFILE_MAX_BYTES, backupCount=10,
        encoding="utf-8"
    )
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    # Get logger
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    # Add handler to logger
    logger.addHandler(handler)
    logger.propagate = False
    return logger


# ........................
def logit(logger, msg, refname="", log_level=logging.INFO):
    """Log a message.

    Args:
        msg (str): A message to write to the logger.
        refname (str): Class or function name to use in logging message.
        log_level (int): A level to use when logging the message.
    """
    if logger is not None:
        logger.log(log_level, refname + ": " + msg)

# ----------------------------------------------------
def get_client(profile, service):
    session = boto3.Session(profile_name=profile)
    client = session.client(service)
    return client


# ----------------------------------------------------
def create_token(type):
    token = f"{type}_{datetime.datetime.now().timestamp()}"
    return token

# ----------------------------------------------------
def get_user_data(script_filename):
    try:
        with open(script_filename, "r") as infile:
            script_text = infile.read()
    except:
        return None
    else:
        text_bytes = script_text.encode("ascii")
        text_base64_bytes = base64.b64encode(text_bytes)
        base64_script_text = text_base64_bytes.decode("ascii")
        return base64_script_text

# ----------------------------------------------------
def _define_spot_launch_template_data(
        spot_template_name, security_group_id, script_filename, key_name):
    user_data_64 = get_user_data(script_filename)
    launch_template_data = {
        "EbsOptimized": True,
        "IamInstanceProfile":
            {
                # "Arn":
                #     "arn:aws:iam::321942852011:instance-profile/AmazonEMR-InstanceProfile-20230404T163626",
                 "Name": "AmazonEMR-InstanceProfile-20230404T163626"
            },
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "Encrypted": False,
                    "DeleteOnTermination": True,
                    # "SnapshotId": "snap-0a6ff81ccbe3194d1",
                    "VolumeSize": 50, "VolumeType": "gp2"
                }
            }
        ],
        "NetworkInterfaces": [
            {
                "AssociatePublicIpAddress": True,
                "DeleteOnTermination": True,
                "Description": "",
                "DeviceIndex": 0,
                "Groups": [security_group_id],
                "InterfaceType": "interface",
                "Ipv6Addresses": [],
                # "PrivateIpAddresses": [
                #     {"Primary": True, "PrivateIpAddress": "172.31.16.201"}
                # ],
                # "SubnetId": "subnet-0beb8b03a44442eef",
                # "NetworkCardIndex": 0
            }
        ],
        "ImageId": "ami-0a0c8eebcdd6dcbd0",
        "InstanceType": "t4g.medium",
        "KeyName": key_name,
        "Monitoring": {"Enabled": False},
        "Placement": {
            "AvailabilityZone": "us-east-1c", "GroupName": "", "Tenancy": "default"
        },
        "DisableApiTermination": False,
        "InstanceInitiatedShutdownBehavior": "terminate",
        "UserData": user_data_64,
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "TemplateName", "Value": spot_template_name}]
            }
        ],
        "InstanceMarketOptions": {
            "MarketType": "spot",
            "SpotOptions": {
                "MaxPrice": "0.033600",
                "SpotInstanceType": "one-time",
                "InstanceInterruptionBehavior": "terminate"
            }
        },
        "CreditSpecification": {"CpuCredits": "unlimited"},
        "CpuOptions": {"CoreCount": 2, "ThreadsPerCore": 1},
        "CapacityReservationSpecification": {"CapacityReservationPreference": "open"},
        "HibernationOptions": {"Configured": False},
        "MetadataOptions": {
            "HttpTokens": "optional",
            "HttpPutResponseHopLimit": 1,
            "HttpEndpoint": "enabled",
            "HttpProtocolIpv6": "disabled",
            "InstanceMetadataTags": "disabled"
        },
        "EnclaveOptions": {"Enabled": False},
        "PrivateDnsNameOptions": {
            "HostnameType": "ip-name",
            "EnableResourceNameDnsARecord": True,
            "EnableResourceNameDnsAAAARecord": False},
        "MaintenanceOptions": {"AutoRecovery": "default"},
        "DisableApiStop": False
    }
    return launch_template_data
    # spot_template_data = {
    #     "IamInstanceProfile": {
    #         "Arn": "customer-mc-ec2-instance-profile-s3",
    #         "Name": "string"
    #     },
    #     "BlockDeviceMappings": [
    #         {"DeviceName": "/dev/xvda",
    #          "Ebs": {
    #              "Encrypted": False,
    #              "DeleteOnTermination": True,
    #              "Iops": 3000,
    #              "VolumeSize": 8,
    #              "VolumeType": "gp3",
    #              "Throughput": 125}
    #          }
    #     ],
    #     "NetworkInterfaces": [
    #         {"AssociatePublicIpAddress": True,
    #          "DeleteOnTermination": True,
    #          "DeviceIndex": 0,
    #          "Groups": [security_group_id],
    #          }
    #     ],
    #     "ImageId": "ami-06ca3ca175f37dd66",
    #     "InstanceType": "t2.small",
    #     "KeyName": "aimee-aws-key",
    #     "Monitoring": {"Enabled": False},
    #     # "Placement": {"AvailabilityZone": "us-east-1c", "GroupName": "", "Tenancy": "default"},
    #     "DisableApiTermination": False,
    #     "InstanceInitiatedShutdownBehavior": "terminate",
    #     "UserData": user_data,
    #     "TagSpecifications": [
    #         {"ResourceType": "instance",
    #          # Include this tag for query to return instances started with this template
    #          "Tags": [
    #              {"Key": "TemplateName", "Value": spot_template_name}
    #          ]}
    #     ],
    #     "InstanceMarketOptions": {
    #         "MarketType": "spot",
    #         "SpotOptions": {
    #             "MaxPrice": "0.083200",
    #             "SpotInstanceType": "one-time",
    #             "InstanceInterruptionBehavior": "terminate"
    #         }
    #     },
    #     "CreditSpecification": {"CpuCredits": "unlimited"},
    #     "CapacityReservationSpecification": {"CapacityReservationPreference": "open"},
    #     "HibernationOptions": {"Configured": False},
    #     "MetadataOptions": {
    #         "HttpTokens": "required",
    #         "HttpPutResponseHopLimit": 2,
    #         "HttpEndpoint": "enabled",
    #         "HttpProtocolIpv6": "disabled",
    #         "InstanceMetadataTags": "disabled"},
    #     "EnclaveOptions": {"Enabled": False},
    #     "PrivateDnsNameOptions": {
    #         "HostnameType": "ip-name",
    #         "EnableResourceNameDnsARecord": True,
    #         "EnableResourceNameDnsAAAARecord": False
    #     },
    #     "MaintenanceOptions": {"AutoRecovery": "default"},
    # }
    # return spot_template_data


# --------------------------------------------------------------------------------------
# On local machine: Describe the launch_template with the template_name
def get_launch_template(template_name):
    ec2_client = boto3.client("ec2")
    lnch_temp = None
    try:
        response = ec2_client.describe_launch_templates(
            LaunchTemplateNames=[template_name],
        )
    except:
        pass
    else:
        # LaunchTemplateName is unique
        try:
            lnch_temp = response["LaunchTemplates"][0]
        except:
            pass
    return lnch_temp

# ----------------------------------------------------
def create_spot_launch_template(
        spot_template_name, security_group_id, script_filename, key_name):
    template = get_launch_template(spot_template_name)
    if template is not None:
        success = True
    else:
        spot_template_data = _define_spot_launch_template_data(
            spot_template_name, security_group_id, script_filename, key_name)
        template_token = create_token("template")
        ec2_client = boto3.client("ec2")
        response = ec2_client.create_launch_template(
            DryRun = False,
            ClientToken = template_token,
            LaunchTemplateName = spot_template_name,
            VersionDescription = "Spot for GBIF process",
            LaunchTemplateData = spot_template_data
        )
        success = (response["ResponseMetadata"]["HTTPStatusCode"] == 200)
    return success


# --------------------------------------------------------------------------------------
# On local machine: Describe all instances with given key_name and/or launch_template_id
def find_instances(key_name, launch_template_name):
    ec2_client = boto3.client("ec2")
    filters = []
    if launch_template_name is not None:
        filters.append({"Name": "tag:TemplateName", "Values": [launch_template_name]})
    if key_name is not None:
        filters.append({"Name": "key-name", "Values": [key_name]})
    response = ec2_client.describe_instances(
        Filters=filters,
        DryRun=False,
        MaxResults=123,
        # NextToken="string"
    )
    instances = []
    try:
        ress = response["Reservations"]
    except:
        pass
    else:
        for res in ress:
            _print_inst_info(res)
            instances.extend(res["Instances"])
    return instances


# --------------------------------------------------------------------------------------
# On local machine: Describe the instance with the instance_id
# --------------------------------------------------------------------------------------
def get_instance(instance_id):
    ec2_client = boto3.client("ec2")
    response = ec2_client.describe_instances(
        InstanceIds=[instance_id],
        DryRun=False,
    )
    try:
        instance = response["Reservations"][0]["Instances"][0]
    except:
        instance = None
    return instance


# ----------------------------------------------------
def run_instance_spot(instance_basename, spot_template_name):
    ec2_client = boto3.client("ec2")
    spot_token = create_token("spot")
    instance_name = create_token(instance_basename)
    response = ec2_client.run_instances(
        # KeyName=key_name,
        ClientToken=spot_token,
        MinCount=1, MaxCount=1,
        LaunchTemplate = {"LaunchTemplateName": spot_template_name, "Version": "1"},
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Name", "Value": instance_name},
                {"Key": "TemplateName", "Value": spot_template_name}
            ]
        }]
    )
    try:
        instance = response["Instances"][0]
    except KeyError:
        instance = None
        print("No instance created")
    return instance["InstanceId"]


# ----------------------------------------------------
def get_launch_template_from_instance(instance_id):
    ec2_client = boto3.client("ec2")
    launch_template_data = ec2_client.get_launch_template_data(InstanceId=instance_id)
    return launch_template_data

# ----------------------------------------------------
def delete_instance(instance_id):
    ec2_client = boto3.client("ec2")
    response = ec2_client.delete_instance(InstanceId=instance_id)
    return response

# ----------------------------------------------------
def create_dataframe_from_gbifcsv_s3_bucket(bucket, csv_path):
    # Read CSV file from S3 into a pandas DataFrame
    s3_client = boto3.client("s3")
    s3_obj = s3_client.get_object(Bucket=bucket, Key=csv_path)
    df = pandas.read_csv(
        s3_obj["Body"], delimiter="\t", encoding="utf-8", low_memory=False,
        quoting=csv.QUOTE_NONE)
    return df


# ----------------------------------------------------
def write_dataframe_to_s3_parquet(df, bucket, parquet_path):
    # Write DataFrame to Parquet format and upload to S3
    s3_client = boto3.client("s3")
    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, engine="pyarrow")
    parquet_buffer.seek(0)
    s3_client.upload_fileobj(parquet_buffer, bucket, parquet_path)

# --------------------------------------------------------------------------------------
# Run on EC2 or local: download from GBIF
# --------------------------------------------------------------------------------------
def download_from_gbif(gbif_basename):
    r = requests.get(f"{GBIF_BASE_URL}{gbif_basename}{ZIP_EXT}", stream=True)
    with open(f"{gbif_basename}{ZIP_EXT}", "wb") as zfile:
        for chunk in r.iter_content(chunk_size=1024):
            # write one chunk at a time to zipfile
            if chunk:
                zfile.write(chunk)

# --------------------------------------------------------------------------------------
# On local machine: Upload local file
# --------------------------------------------------------------------------------------
def extract_occurrences_from_dwca(gbif_basename):
    local_path = "~"
    zipfilename = os.path.join(local_path, f"{gbif_basename}{ZIP_EXT}")
    with zipfile.ZipFile(zipfilename, "r") as zfile:
        zfile.extractall(local_path)

# --------------------------------------------------------------------------------------
# On local machine: Upload local file
# --------------------------------------------------------------------------------------
def upload_to_ec2(local_path, filename, ec2_key, ec2_user, ec2_ip):
    local_filename = os.path.join(local_path, filename)
    cmd = f"scp -i {ec2_key} {local_filename} {ec2_user}@{ec2_ip}:"
    info, err = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    if not err:
        ec2_file = f"/home/{ec2_user}/{filename}"
        print(f"Successfully uploaded {ec2_file} to {ec2_ip}")


# --------------------------------------------------------------------------------------
# Run on EC2 or local: Upload file to S3
# --------------------------------------------------------------------------------------
def upload_to_s3(local_path, filename, dev_bucket, s3_path):
    s3_client = boto3.client("s3")
    local_filename = os.path.join(local_path, filename)
    # ec2_file = f"/home/{ec2_user}/{csv_fname}"
    s3_client.upload_file(local_filename, dev_bucket, s3_path)
    print(f"Successfully uploaded {filename} to s3://{dev_bucket}/{s3_path}")


# --------------------------------------------------------------------------------------
# On local machine: Trim CSV file to named columns and save in parquet format
# --------------------------------------------------------------------------------------
def trim_gbifcsv_to_parquet(local_filename, parquet_filename):
    gbif_dataframe = pandas.read_csv(
        local_filename, delimiter="\t", encoding="utf-8", low_memory=False,
        quoting=csv.QUOTE_NONE)
    # Trim the DataFrame to the subset of fieldnames
    trimmed_gbif_dataframe = gbif_dataframe[FIELD_SUBSET]
    # Write the trimmed DataFrame to Parquet file format
    trimmed_gbif_dataframe.to_parquet(parquet_filename)

def _print_inst_info(reservation):
    resid = reservation["ReservationId"]
    inst = reservation["Instances"][0]
    print(f"ReservationId: {resid}")
    name = temp_id = None
    try:
        tags = inst["Tags"]
    except:
        pass
    else:
        for t in tags:
            if t["Key"] == "Name":
                name = t["Value"]
            if t["Key"] == "aws:ec2launchtemplate:id":
                temp_id = t["Value"]
    ip = inst["PublicIpAddress"]
    state = inst["State"]["Name"]
    print(f"Instance name: {name}, template: {temp_id}, IP: {ip}, state: {state}")

# --------------------------------------------------------------------------------------
# On EC2: Create a trimmed dataframe from CSV and save to S3 in parquet format
# --------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
# if __name__ == "__main__":
key_name = "aimee-aws-key"
aws_zone = "us-east-1"
# Allows KU Dyche hall
security_group_id = "sg-0b379fdb3e37389d1"

# Local machine data
local_ec2_key = f"/home/astewart/.ssh/{key_name}.pem"
local_path = "/mnt/sata8/tank/testgbif/occ_2023_06_23"
test_basename = "occurrence_100k"
gbif_basename = "0042658-230530130749713"
csv_fname = f"{test_basename}.csv"

# S3
dev_bucket = "specify-network-dev"
bucket_path = "gbif_test/gbif_dwc_extract"
# s3_csv_path = f"{bucket_path}/{test_basename}.csv"
# s3_parquet_path = f"{bucket_path}/{test_basename}.parquet"

# EC2 persistent
ec2_user = "ubuntu"
ec2_dev_ip = "54.156.84.82"

# EC2 Spot Instance
iam_user = "arn:aws:iam::321942852011:user/aimee.stewart"
spot_template_name = "specnet_launch_template"
instance_basename = "specnet_analyst"

script_filename = "tests/user_data_for_ec2spot.sh"

target_capactity_spec = {
    "TotalTargetCapacity": 1,
    "SpotTargetCapacity": 1,
    "DefaultTargetCapacityType": "spot"
}
spot_opts = {
    "AllocationStrategy": "price-capacity-optimized",
    "InstanceInterruptionBehavior": "terminate"
}
launch_template_config = {
    "LaunchTemplateSpecification": {
    "LaunchTemplateName": spot_template_name,
    "Version": "1"
    }
}

# -------  Find or create template -------
success = create_spot_launch_template(
        spot_template_name, security_group_id, script_filename, key_name)

# -------  Run instance from template -------
instance_id = run_instance_spot(instance_basename, spot_template_name)

instance = get_instance(instance_id)
ip = instance["PublicIpAddress"]
