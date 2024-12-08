from datasets import load_dataset
from tqdm import tqdm
from typing import List, Dict
import re, inspect, copy
from dataclasses import dataclass


# Define the data class
@dataclass
class Sample:
    Input: str
    Output: str

correctness = []

############################################################################################################define basic tools

def construct_prompt_and_call_model(sample, agent):
    print("------------------------------------------------------")
    print("question:", sample.Input)
    response = agent.step(sample.Input)
    call = response.msgs[0].content
    print("answer:", call)
    agent.reset()
    return call

def eval_nexus_dataset(model, dataset_name):

    if dataset_name == "NVDLibrary":
        dataset = load_dataset("Nexusflow/NVDLibraryBenchmark")["train"]
        dataset = [Sample(sample["Input"], sample["Output"].replace("r = nvdlib.", "")) for sample in dataset]

    elif dataset_name == "VirusTotal":
        dataset = load_dataset("Nexusflow/VirusTotalBenchmark")["train"]
        dataset = [Sample(sample["Input"], sample["Output"]) for sample in dataset]

    elif dataset_name == "Places API":
        dataset = load_dataset("Nexusflow/PlacesAPIBenchmark")["train"]
        dataset = [Sample(sample["Input"], sample["Output"]) for sample in dataset]

    elif dataset_name == "Climate API":
        dataset = load_dataset("Nexusflow/ClimateAPIBenchmark")["train"]
        dataset = [Sample(sample["Input"], sample["Output"]) for sample in dataset]

    elif dataset_name == "OTX":
        dataset = load_dataset("Nexusflow/OTXAPIBenchmark")["train"]
        dataset = [Sample(sample["Input"], sample["Output"]) for sample in dataset]

    elif dataset_name == "VirusTotal-Nested Calls":
        dataset = load_dataset("Nexusflow/vt_multiapi")["train"]
        dataset = [Sample(sample["generated_question"], "".join(sample["fncall"])) for sample in dataset if len(sample["fncall"]) == 1]

    elif dataset_name == "VirusTotal-Parallel Calls":
        dataset = load_dataset("Nexusflow/vt_multiapi")["train"]
        dataset = [Sample(sample["generated_question"], "; ".join(sample["fncall"])) for sample in dataset if len(sample["fncall"]) > 1]

    elif dataset_name == "NVDLibrary-Nested Calls":
        dataset = load_dataset("Nexusflow/CVECPEAPIBenchmark")["train"]
        dataset = [Sample(sample["Input"], "".join(sample["Output"])) for sample in dataset]

    print (f"Benchmarking {dataset_name} ON {model}")
    pbar = tqdm(dataset, desc="Booting...")
    accuracy = evaluate_and_print_accuracy(pbar, model)
    return accuracy


############################################################################################################
def evaluate_and_print_accuracy(pbar, model):
    global correctness
    accuracy_list = []
    for sample in pbar:
        old_len = len(correctness)
        # Using the data class instance in the prompt
        ground_truth = sample.Output

        call = construct_prompt_and_call_model(sample, model)
        if call and bool(re.match(r'\w+\(.*\)', call)):
            try:
                exec(call)
            except Exception as e:
                print (e)
                pass
        new_len = len(correctness)
        # Ensure that the function was correctly called.
        if old_len < new_len:
            gpt_call = copy.deepcopy(correctness)
            correctness = []
            exec(ground_truth.strip())
            gt_call = copy.deepcopy(correctness)
            accuracy = gpt_call == gt_call
            correctness = []
            if(gpt_call == gt_call):
                print("True!")
            else:
                print("False!")
            print(f"Generated call: {gpt_call}")
            print(f"Groundtru call: {gt_call}")
        else:
            gpt_call = "invalid call"
            accuracy = 0
            print("invalid call")
        accuracy_list.append(accuracy)
        pbar.set_description(f"Accuracy: {sum(accuracy_list)/len(accuracy_list):.4f}")

    accuracy = sum(accuracy_list)/len(accuracy_list)
    print (f"Final Accuracy: {accuracy}")
    return accuracy

### NVDLibrary API Benchmarking

def searchCVE(cpeName=None, cveId=None, cvssV2Metrics=None, cvssV2Severity=None, cvssV3Metrics=None, cvssV3Severity=None, cweId=None, hasCertAlerts=None, hasCertNotes=None, hasKev=None, hasOval=None, isVulnerable=None, keywordExactMatch=None, keywordSearch=None, lastModStartDate=None, lastModEndDate=None, noRejected=None, pubStartDate=None, pubEndDate=None, sourceIdentifier=None, versionEnd=None, versionEndType=None, versionStart=None, versionStartType=None, virtualMatchString=None, limit=None, delay=None, key=None, verbose=None):
    """
    Build and send GET request then return list of objects containing a collection of CVEs. For more information on the parameters available, please visit https://nvd.nist.gov/developers/vulnerabilities

    When providing ANY date time strings, please also specify the time. Such as: "00:00" suffix to the end of every datetime string. So, if you're generating a date, make sure to say "2023-03-01 00:00".

    cpeName (str): Please do not confuse this with keywordSearch; this requires the argument to start with "cpe", whereas the keywordSearch argument allows for arbitrary keywords. This value will be compared agains the CPE Match Criteria within a CVE applicability statement. (i.e. find the vulnerabilities attached to that CPE). Partial match strings are allowed.
    cveId (str): Please pass in a string integer, like "1" or "30". Returns a single CVE that already exists in the NVD.
    cvssV2Metrics (str): This parameter returns only the CVEs that match the provided CVSSv2 vector string. Either full or partial vector strings may be used. This parameter cannot be used in requests that include cvssV3Metrics.
    cvssV2Severity (str): Find vulnerabilities having a LOW, MEDIUM, or HIGH version 2 severity.
    cvssV3Metrics (str): This parameter returns only the CVEs that match the provided CVSSv3 vector string. Either full or partial vector strings may be used. This parameter cannot be used in requests that include cvssV2Metrics.
    cvssV3Severity (str): Find vulnerabilities having a LOW, MEDIUM, HIGH, or CRITICAL version 3 severity.
    cweId (str): Filter collection by CWE (Common Weakness Enumeration) ID. You can find a list at https://cwe.mitre.org/. A CVE can have multiple CWE IDs assigned to it. Examples include "CVE-34".
    hasCertAlerts (bool): Returns CVE that contain a Technical Alert from US-CERT.
    hasCertNotes (bool): Returns CVE that contain a Vulnerability Note from CERT/CC.
    hasOval (bool): Returns CVE that contain information from MITRE's Open Vulnerability and Assessment Language (OVAL) before this transitioned to the Center for Internet Security (CIS).
    isVulnerable (bool): Returns CVE associated with a specific CPE, where the CPE is also considered vulnerable. REQUIRES cpeName parameter. isVulnerable is not compatible with virtualMatchString parameter.
    keywordExactMatch (bool): When keywordSearch is used along with keywordExactmatch, it will search the NVD for CVEs containing exactly what was passed to keywordSearch. REQUIRES keywordSearch.
    keywordSearch (str): Searches CVEs where a word or phrase is found in the current description. If passing multiple keywords with a space character in between then each word must exist somewhere in the description, not necessarily together unless keywordExactMatch=True is passedto searchCVE.
    lastModStartDate (str): Include the time, such as "2023-03-01 00:00". These parameters return only the CVEs that were last modified during the specified period. If a CVE has been modified more recently than the specified period, it will not be included in the response. If filtering by the last modified date, both lastModStartDate and lastModEndDate are REQUIRED. The maximum allowable range when using any date range parameters is 120 consecutive days. Example includes "2023-03-01 00:00".
    lastModEndDate (str, datetime obj): Include the time, such as "2023-03-01 00:00". Required if using lastModStartDate. Example includes "2023-03-01 00:00".
    noRejected (bool): Filters out all CVEs that are in a reject or rejected status. Searches without this parameter include rejected CVEs.
    pubStartDate (str,datetime obj): Include the time, such as "2023-03-01 00:00". These parameters return only the CVEs that were added to the NVD (i.e., published) during the specified period. If filtering by the published date, both pubStartDate and pubEndDate are REQUIRED. The maximum allowable range when using any date range parameters is 120 consecutive days. Example includes "2023-03-01 00:00".
    pubEndDate (str, datetime obj): Include the time, such as "2023-03-01 00:00". Required if using pubStartDate. Examples include "2023-03-01 00:00".
    sourceIdentifier (str): Returns CVE where the data source of the CVE is the value that is passed to sourceIdentifier.
    versionEnd (str): Must be combined with versionEndType and virtualMatchString. Returns only the CVEs associated with CPEs in specific version ranges.
    versionEndType (str): Must be combined with versionEnd and virtualMatchString. Valid values are including or excluding. Denotes to include the specified version in versionEnd, or exclude it.
    versionStart (str): Must be combined with versionStartType and virtualMatchString. Returns only CVEs with specific versions. Requests that include versionStart cannot include a version component in the virtualMatchString.
    versionStartType (str): Must be combined with versionStart and virtualMatchString. Valid values are including or excluding. Denotes to include the specified version in versionStart, or exclude it.
    virtualMatchString (str): A more broad filter compared to cpeName. The cpe match string that is passed to virtualMatchString is compared against the CPE Match Criteria present on CVE applicability statements.
    limit (int): Custom argument to limit the number of results of the search. Allowed any number between 1 and 2000.
    delay (int): Can only be used if an API key is provided. This allows the user to define a delay. The delay must be greater than 0.6 seconds. The NVD API recommends scripts sleep for atleast 6 seconds in between requests.
    key (str): NVD API Key. Allows for the user to define a delay. NVD recommends scripts sleep 6 seconds in between requests. If no valid API key is provided, requests are sent with a 6 second delay.
    verbose (bool): Prints the URL request for debugging purposes.
    """
    correctness.append({"searchCVE" : locals()})

def searchCPE(cpeNameId=None, cpeMatchString=None, keywordExactMatch=None, keywordSearch=None, lastModStartDate=None, lastModEndDate=None, matchCriteriaId=None, limit=None, key=None, delay=None, verbose=None):
    """
    Build and send GET request then return list of objects containing a collection of CPEs.

    When providing ANY date time strings, please also specify the time. Such as: "00:00" suffix to the end of every datetime string. So, if you're generating a date, make sure to say "2023-03-01 00:00".

    cpeNameId (str) – Returns a specific CPE record using its UUID. If a correctly formatted UUID is passed but it does not exist, it will return empty results. The UUID is the cpeNameId value when searching CPE.
    cpeMatchString (str) – Use a partial CPE name to search for other CPE names.
    keywordExactMatch (bool) – Searches metadata within CPE title and reference links for an exact match of the phrase or word passed to it. Must be included with keywordSearch.
    keywordSearch (str) – Returns CPE records where a word or phrase is found in the metadata title or reference links. Space characters act as an AND statement.
    lastModStartDate (str) - Include the time!! CPE last modification start date. Maximum 120 day range. A start and end date is required. All times are in UTC 00:00. A datetime object or string can be passed as a date. NVDLib will automatically parse the datetime object into the correct format. String Example: ‘2020-06-28 00:00’
    lastModEndDate (str) – Include the time!! CPE last modification end date. Maximum 120 day range. Must be included with lastModStartDate. String Example: ‘2020-06-28 00:00’.
    limit (int) – Limits the number of results of the search.
    key (str) – NVD API Key. Allows for a request every 0.6 seconds instead of 6 seconds.
    delay – Can only be used if an API key is provided. The amount of time to sleep in between requests. Must be a value above 0.6 seconds if an API key is present. delay is set to 6 seconds if no API key is passed.
    verbose (bool) – Prints the URL request for debugging purposes.
    """
    correctness.append({"searchCPE" : locals()})

nvd_tools = [searchCVE,
             searchCPE]


### VirusTotal API Benchmarking

def vt_get_dns_resolution_object(id: str, x_apikey: str):
    """
    This endpoint retrieves a Resolution object by its ID. A resolution object ID is made by appending the IP and the domain it resolves to together.

    Domain-IP resolutions. Resolution objects include the following attributes:
    date: <integer> date when the resolution was made (UTC timestamp).
    host_name: <string> domain or subdomain requested to the resolver.
    host_name_last_analysis_stats: <dictionary> last detection stats from the resolution's domain. Similar to the domains's last_analysis_stats attribute.
    ip_address: <string> IP address the domain was resolved to.
    ip_address_last_analysis_stats: <dictionary> last detection stats from the resolution's IP address. Similar to the IP address' last_analysis_stats attribute.
    resolver: <string> source of the resolution.

    Args:
    - id: string, required, Resolution object ID
    - x-apikey: string, required, Your API key
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_dns_resolution_object': return_dict})

def vt_get_objects_related_to_ip_address(ip: str, relationship: str, x_apikey: str, limit: int = None, cursor: str = None):
    """
    IP addresses have number of relationships to other objects. This returns ALL objects that fit the relationship.

    The relationships are documented here:
    - comments: The comments for the IP address. Returns a list of comments.
    - communicating_files: Files that communicate with the IP address. Returns a list of files.
    - downloaded_files: Files downloaded from the IP address. VT Enterprise users only. Returns a list of files.
    - graphs: Graphs including the IP address. Returns a list of graphs.
    - historical_ssl_certificates: SSL certificates associated with the IP. Returns a list of SSL certificates.
    - historical_whois: WHOIS information for the IP address. Retrurns a list of Whois attributes.
    - related_comments: Community posted comments in the IP's related objects. Returns a list of comments.
    - related_references: Returns the references related to the IP address. Returns a list of References.
    - related_threat_actors: Threat actors related to the IP address. Returns a list of threat actors.
    - referrer_files: Files containing the IP address. Returns a list of Files.
    - resolutions: Resolves the IP addresses. Returns a list of resolutions.
    - urls: Returns a list of URLs related to the IP address. Returns a list of URLs.

    Args:
    - ip, string, required, IP address
    - relationship, string, required, Relationship name (see the list of items from above)
    - x-apikey, string, required, Your API key
    - limit, int32, optional, Maximum number of comments to retrieve
    - cursor, string, optional, Continuation cursor
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_objects_related_to_ip_address': return_dict})

def vt_get_ip_address_report(ip: str, x_apikey: str):
    """
    Retrieve an IP address report. These reports condense all of the recent activity that VirusTotal has seen for the resource under consideration, as well as contextual information about it.
    This function specifically generates these reports using the IP address parameter.

    Args:
    - ip: string, required, IP address
    - x-apikey: string, required, Your API key
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_ip_address_report': return_dict})

def vt_add_votes_to_ip_address(ip: str, data: dict, x_apikey: str):
    """
    With this function you can post a vote for a given file. The body for the POST request must be the JSON representation of a vote object. Note however that you don't need to provide an ID for the object, as they are automatically generated for new votes. The verdict attribute must have be either harmless or malicious.

    Please ensure that the JSON object you provide conforms accurately to valid JSON standards.

    Args:
    - ip, string, required, IP address
    - data, json, Vote object
    - x-apikey, string, required, Your API key
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_add_votes_to_ip_address': return_dict})

def vt_get_domain_report(domain: str, x_apikey: str):
    """
    Retrieves a domain report. These reports contain information regarding the domain itself that VirusTotal has collected.

    Args:
    - domain: string, required, Domain name
    - x-apikey: string, required, Your API key
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_domain_report': return_dict})

def vt_get_comments_on_ip_address(ip: str, x_apikey: str, limit: int = None, cursor: str = None):
    """
    Retrieves the comments on a provided IP address. Returns a list of Comment objects.

    Args:
    - ip, string, required, IP address
    - x-apikey, string, required, Your API key
    - limit, int32, optional, Maximum number of comments to retrieve
    - cursor, string, optional, Continuation cursor
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_comments_on_ip_address': return_dict})

def vt_add_comment_to_ip_address(ip: str, data: dict, x_apikey: str):
    """
    With this function you can post a comment for a given IP address. The body for the POST request must be the JSON representation of a comment object. Notice however that you don't need to provide an ID for the object, as they are automatically generated for new comments.
    However, please note that you will need to provide a valid data JSON for using this function.

    Any word starting with # in your comment's text will be considered a tag, and added to the comment's tag attribute.

    Returns a Comment object.

    Args:
    - ip: string, required, IP address
    - data: json, required, A comment object
    - x-apikey: string, required, Your API key
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_add_comment_to_ip_address': return_dict})

def vt_get_object_descriptors_related_to_ip_address(ip: str, relationship: str, x_apikey: str, limit: int = None, cursor: str = None):
    """
    This specifically returns related object's IDs (and context attributes, if any). Please note that this will not return all attributes.

    You are expected to provide the relationship to the object you're interested in. The valid relationships are as follows.

    The relationships are documented here:
    - comments: The comments for the IP address.
    - communicating_files: Files that communicate with the IP address.
    - downloaded_files: Files downloaded from the IP address. VT Enterprise users only.
    - graphs: Graphs including the IP address.
    - historical_ssl_certificates: SSL certificates associated with the IP.
    - historical_whois: WHOIS information for the IP address. Retrurns a list of Whois attributes.
    - related_comments: Community posted comments in the IP's related objects.
    - related_references: Returns the references related to the IP address.
    - related_threat_actors: Threat actors related to the IP address.
    - referrer_files: Files containing the IP address.
    - resolutions: Resolves the IP addresses.
    - urls: Returns a list of URLs related to the IP address.

    Here are some useful descriptions of the arguments in this API, with the format - name of this argument: type of the data, required or optional, description of this argument.
    - ip: string, required, IP address
    - relationship: string, required, Relationship name (see table)
    - x-apikey: string, required, Your API key
    - limit: int32, optional, Maximum number of comments to retrieve
    - cursor: string, optional, Continuation cursor
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_object_descriptors_related_to_ip_address': return_dict})

def vt_get_objects_related_to_domain(domain: str, relationship: str, x_apikey: str, limit: int = None, cursor: str = None):
    """
    Objects are a key concept in the VirusTotal API. Each object has an identifier and a type.
    Each object has an associated URL, and each domain is associated with objects.
    This function returns ALL of the objects related to the domain, based on the specified relationship.

    The following describe the valid relationship:
    - caa_records: Records CAA for the domain.
    - cname_records: Records CNAME for the domain.
    - comments: Community posted comments about the domain.
    - communicating_files: Files that communicate with the domain.
    - downloaded_files: Files downloaded from that domain.
    - graphs: All graphs that include the domain.
    - historical_ssl_certificates: SSL certificates associated with the domain.
    - historical_whois: WHOIS information for the domain.
    - immediate_parent: Domain's immediate parent.
    - mx_records: Records MX for the domain.
    - ns_records: Records NS for the domain.
    - parent: Domain's top parent.
    - referrer_files: Refers to any and all files that contain this domain.
    - related_comments: Community posted comments in the domain's related objects.
    - related_references: Refers to the References related to the domain.
    - related_threat_actors: Refers to the threat actors related to the domain. A list of Threat Actors.
    - resolutions: DNS resolutions for the domain.
    - soa_records: Records SOA for the domain.
    - siblings: Refers to the Domain's sibling domains.
    - subdomains: Refers to the Domain's subdomains.
    - urls: Refers to the URLs that contain this domain.
    - user_votes: Refers to the current user's votes.


    Args:
    - domain: string, required, Domain name
    - relationship, string, required, Relationship name (see table)
    - x-apikey, string, required, Your API key
    - limit, int32, optional, Maximum number of comments to retrieve
    - cursor, string, optional, Continuation cursor
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_objects_related_to_domain': return_dict})

def vt_get_object_descriptors_related_to_domain(domain: str, relationship: str, x_apikey: str, limit: int = None, cursor: str = None):
    """
    This specifically returns related object's IDs (and context attributes, if any). Please note that this will not return all attributes. This will return objects relating to a domain.

    - caa_records: Records CAA for the domain.
    - cname_records: Records CNAME for the domain.
    - comments: Community posted comments about the domain.
    - communicating_files: Files that communicate with the domain.
    - downloaded_files: Files downloaded from that domain.
    - graphs: All graphs that include the domain.
    - historical_ssl_certificates: SSL certificates associated with the domain.
    - historical_whois: WHOIS information for the domain.
    - immediate_parent: Domain's immediate parent.
    - mx_records: Records MX for the domain.
    - ns_records: Records NS for the domain.
    - parent: Domain's top parent.
    - referrer_files: Refers to any and all files that contain this domain.
    - related_comments: Community posted comments in the domain's related objects.
    - related_references: Refers to the References related to the domain.
    - related_threat_actors: Refers to the threat actors related to the domain. A list of Threat Actors.
    - resolutions: DNS resolutions for the domain.
    - soa_records: Records SOA for the domain.
    - siblings: Refers to the Domain's sibling domains.
    - subdomains: Refers to the Domain's subdomains.
    - urls: Refers to the URLs that contain this domain.
    - user_votes: Refers to the current user's votes.

    Args:
    - domain: string, required, Domain name
    - relationship: string, required, Relationship name (see table)
    - x-apikey: string, required, Your API key
    - limit: int32, optional, Maximum number of comments to retrieve
    - cursor: string, optional, Continuation cursor
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_object_descriptors_related_to_domain': return_dict})

def vt_get_comments_on_domain(domain: str, x_apikey: str, limit: int = None, cursor: str = None):
    """
    This function will retrieve comments on a specified domain.

    Args:
    - domain, string, required, Domain name
    - x-apikey, string, required, Your API key
    - limit, int32, optional, Maximum number of comments to retrieve
    - cursor, string, optional, Continuation cursor
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_comments_on_domain': return_dict})

def vt_get_votes_on_ip_address(ip: str):
    """
    This function will retrieve votes on a provided IP address.

    Args:
    - ip: string, required, ip address
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'vt_get_votes_on_ip_address': return_dict})

vt_tools = [vt_get_dns_resolution_object,
            vt_get_objects_related_to_ip_address,
            vt_get_ip_address_report,
            vt_add_votes_to_ip_address,
            vt_get_domain_report,
            vt_get_comments_on_ip_address,
            vt_add_comment_to_ip_address,
            vt_get_object_descriptors_related_to_ip_address,
            vt_get_objects_related_to_domain,
            vt_get_object_descriptors_related_to_domain,
            vt_get_comments_on_domain,
            vt_get_votes_on_ip_address]


### Places API Benchmarking

def get_current_location() -> str:
    """
    Returns the current location. ONLY use this if the user has not provided an explicit location in the query.
    """
    args_dict = locals()
    global correctness
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({"get_current_location" : return_dict})

def sort_results(places, sort: str, ascending: bool) -> List:
    """
    Sorts the results by either 'distance', 'rating' or 'price'.

    Args
    - places: The output list from the recommendations.
    - sort (str): If set, sorts by either 'distance' or 'rating' or 'price'. ONLY supports 'distance' or 'rating' or 'price'.
    - ascending (bool): If ascending is set, setting this boolean to true will sort the results by lower values first.
    """
    args_dict = locals()
    global correctness
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({"sort_results" : return_dict})

def get_latitude_longitude(location: str) -> List:
    """
    Given a city name, this function provides the latitude and longitude of the specific location.

    Args
    - location: This can be a city like 'Austin', or a place like 'Austin Airport', etc.
    """
    args_dict = locals()
    global correctness
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({"get_latitude_longitude" : return_dict})

def get_distance(place_1: str, place_2: str):
    """
    Provides distance between two locations. Do NOT provide latitude longitude, but rather, provide the string descriptions.

    Args
    - place_1: The first location.
    - place_2: The second location.
    """
    args_dict = locals()
    global correctness
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({"get_distance" : return_dict})

def get_recommendations(topics: list, lat_long: tuple):
    """
    Returns the recommendations for a specific topic that is of interest. Remember, a topic IS NOT an establishment. For establishments, please use anothher function.

    Args
    - topics (list): A list of topics of interest to pull recommendations for. Can be multiple words.
    - lat_long (tuple): The lat_long of interest.
    """
    args_dict = locals()
    global correctness
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({"get_recommendations" : return_dict})

def find_places_near_location(type_of_place: list, location: str, radius_miles: int = 50) -> List[Dict]:
    """
    Find places close to a very defined location.

    Args
    - type_of_place (list): The type of place. This can be something like 'restaurant' or 'airport'. Make sure that it is a physical location. You can provide multiple words.
    - location (str): The location for the search. This can be a city's name, region, or anything that specifies the location.
    - radius_miles (int): Optional. The max distance from the described location to limit the search. Distance is specified in miles.
    """
    args_dict = locals()
    global correctness
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({"find_places_near_location" : return_dict})

def get_some_reviews(place_names: list, location: str = None):
    """
    Given an establishment (or place) name, return reviews about the establishment.

    Args
    - place_names (list): The name of the establishment. This should be a physical location name. You can provide multiple inputs.
    - location (str) : The location where the restaurant is located. Optional argument.
    """
    args_dict = locals()
    global correctness
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({"get_some_reviews" : return_dict})

places_tools = [get_current_location,
                sort_results,
                get_latitude_longitude,
                get_distance, 
                get_recommendations, 
                find_places_near_location, 
                get_some_reviews]

### Climate API Benchmarking


def get_latitude_longitude(location: str) -> List:
    """
    Given a city name, this function provides the latitude and longitude of the specific location.

    Args:
    - location: This can be a city like 'Austin', or a place like 'Austin Airport', etc.
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'get_latitude_longitude': return_dict})

def get_current_location() -> str:
    """
    Returns the current location. ONLY use this if the user has not provided an explicit location in the query.

    Returns a string representation of the city, such as "Austin". This will not return a latitude or longitude.
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'get_current_location': return_dict})

def find_nearby_stations(lat_long : tuple):
    """
    This endpoint provides a list of nearby weather stations for a given geographical location. Please provide the geographical location as a latitude and longitude.

    Args:
        - lat_long: This argument should be a tuple of the latitude as the first element and the longitude as the second element.

    Returns:
        - A list of dictionaries about the various stations near you.
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'find_nearby_stations': return_dict})

def get_nearest_station_id(nearby_stations):
    """
    Given a list of nearby stations, returns the one nearest to you and provides the system ID for it alone.

    Args:
        - nearby_stations: A list of nearby stations in dictionary format.

    Returns:
        The station_id alone for the nearest station in the list of the stations provided.
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'get_nearest_station_id': return_dict})

def get_timezone(lat_long):
    """
    This gets the timezone for a given latlong.

    Args:
      - lat_long: The latitude and longitude of the area you want to query the timezone for.
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'get_timezone': return_dict})

def get_hourly_observation(station_id, start_time, end_time, time_zone):
    """
    Returns hourly observations between start_time and end_time.

    Please ensure that the start and end times are provided in the format "YYYY-MM-DD".
    Please provide the timezone for your input as well!

    Args:
        - station_id: The station_id for the station you're interested in
        - start_time : The time span to start pulling hourly observations for. Should be in format of "YYYY-MM-DD".
        - end_time: The time span to end pulling hourly observations for. Should be in format of "YYYY-MM-DD".
        - timezone: The timezone string id for the location you're asking for.

    Returns:
        The list of hourly observations for your station and timespan.
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'get_hourly_observation': return_dict})

def subtract_time_delta(date_time_str, delta_days):
    """
    Subtracts a time delta from the date part of a given date time string and returns
    the new date string with the updated date.

    DO NOT use this if delta_days is 0.

    :param date_time_str: The date time string in format 'YYYY-MM-DD'.
    :param delta_days: Number of days to subtract. HAS TO BE LARGER THAN 0.
    :return: New date string with the updated date after subtracting the delta.
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'subtract_time_delta': return_dict})

def get_current_time_at_location(lat_long):
    """
    Returns the current time at a given location.

    Args:
      - lat_long: The latitude and longitude of the location of interest.
    """
    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'get_current_time_at_location': return_dict})

climate_tools = [get_latitude_longitude,
                 get_current_location,
                 find_nearby_stations,
                 get_nearest_station_id,
                 get_timezone,
                 get_hourly_observation,
                 get_hourly_observation,
                 subtract_time_delta,
                 get_current_time_at_location,
                 get_current_time_at_location]


### OTX API Benchmarking

def getIndicatorForIPv4(apiKey: str, ip: str, section: str):
    """
    Retrieves comprehensive information for a specific IPv4 address from the AlienVault database. This function provides varied data types. 'general' section includes general information about the IP, geo data, and lists of other available sections. 'reputation' provides OTX data on observed malicious activity by AlienVault Labs. 'geo' details extensive geographic data such as country code and coordinates. 'malware' section shows malware samples associated with the IP, 'urlList' reveals URLs linked to the IP, and 'passiveDns' offers passive DNS information about hostnames/domains associated with the IP.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - ip: string, required, IPv4 address to query
    - section: string, required, Specific data section to retrieve (options: general, reputation, geo, malware, urlList, passiveDns)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForIPv4': return_dict})

def getIndicatorForIPv6(apiKey: str, ip: str, section: str):
    """
    Retrieves comprehensive information for a specific IPv6 address from the AlienVault database. This function allows you to obtain various types of data. The 'general' section provides general information about the IP, including geo data, and a list of other available sections. 'reputation' offers OTX data on malicious activity observed by AlienVault Labs. 'geo' details more verbose geographic data such as country code and coordinates. 'malware' reveals malware samples connected to the IP, and 'urlList' shows URLs associated with the IP. Lastly, 'passiveDns' includes passive DNS information about hostnames/domains pointing to this IP.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - ip: string, required, IPv6 address to query
    - section: string, required, Specific data section to retrieve (options: general, reputation, geo, malware, urlList, passiveDns)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForIPv6': return_dict})

def getIndicatorForDomain(apiKey: str, domain: str, section: str):
    """
    Retrieves a comprehensive overview for a given domain name from the AlienVault database. This function provides various data types about the domain. The 'general' section includes general information about the domain, such as geo data, and lists of other available sections. 'geo' provides detailed geographic data including country code and coordinates. The 'malware' section indicates malware samples associated with the domain. 'urlList' shows URLs linked to the domain, 'passiveDns' details passive DNS information about hostnames/domains associated with the domain, and 'whois' gives Whois records for the domain.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - domain: string, required, Domain address to query
    - section: string, required, Specific data section to retrieve (options: general, geo, malware, urlList, passiveDns, whois)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForDomain': return_dict})

def getIndicatorForHostname(apiKey: str, hostname: str, section: str):
    """
    Retrieves detailed information for a specific hostname from the AlienVault database. This function provides various data types about the hostname. The 'general' section includes general information about the IP, geo data, and lists of other available sections. 'geo' provides detailed geographic data including country code and coordinates. The 'malware' section indicates malware samples associated with the hostname. 'urlList' shows URLs linked to the hostname, and 'passiveDns' details passive DNS information about hostnames/domains associated with the hostname.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - hostname: string, required, Single hostname address to query
    - section: string, required, Specific data section to retrieve (options: general, geo, malware, urlList, passiveDns)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForHostname': return_dict})

def getIndicatorForFileHashes(apiKey: str, fileHash: str, section: str):
    """
    Retrieves information related to a specific file hash from the AlienVault database. This function provides two types of data: 'general', which includes general metadata about the file hash and a list of other available sections for the hash; and 'analysis', which encompasses both dynamic and static analysis of the file, including Cuckoo analysis, exiftool, etc.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - fileHash: string, required, Single file hash to query
    - section: string, required, Specific data section to retrieve (options: general, analysis)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForFileHashes': return_dict})

def getIndicatorForUrl(apiKey: str, url: str, section: str):
    """
    Retrieves information related to a specific URL from the AlienVault database. This function offers two types of data: 'general', which includes historical geographic information, any pulses this indicator is on, and a list of other available sections for this URL; and 'url_list', which provides full results from AlienVault Labs URL analysis, potentially including multiple entries.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - url: string, required, Single URL to query
    - section: string, required, Specific data section to retrieve (options: general, url_list)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForUrl': return_dict})

def getIndicatorForCVE(apiKey: str, cve: str, section: str):
    """
    Retrieves information related to a specific CVE (Common Vulnerability Enumeration) from the AlienVault database. This function offers detailed data on CVEs. The 'General' section includes MITRE CVE data, such as CPEs (Common Platform Enumerations), CWEs (Common Weakness Enumerations), and other relevant details. It also provides information on any pulses this indicator is on, and lists other sections currently available for this CVE.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - cve: string, required, Specific CVE identifier to query (e.g., 'CVE-2014-0160')
    - section: string, required, Specific data section to retrieve ('general' only)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForCVE': return_dict})

def getIndicatorForNIDS(apiKey: str, nids: str, section: str):
    """
    Retrieves metadata information for a specific Network Intrusion Detection System (NIDS) indicator from the AlienVault database. This function is designed to provide general metadata about NIDS indicators.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - nids: string, required, Specific NIDS indicator to query (e.g., '2820184')
    - section: string, required, Specific data section to retrieve ('general' only)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForNIDS': return_dict})

def getIndicatorForCorrelationRules(apiKey: str, correlationRule: str, section: str):
    """
    Retrieves metadata information related to a specific Correlation Rule from the AlienVault database. This function is designed to provide general metadata about Correlation Rules used in network security and event correlation. Correlation Rules are crucial for identifying patterns and potential security threats in network data.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - correlationRule: string, required, Specific Correlation Rule identifier to query (e.g., '572f8c3c540c6f0161677877')
    - section: string, required, Specific data section to retrieve ('general' only)
    """

    args_dict = locals()
    global correctness
    return_dict = {
    }
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value

    correctness.append({'getIndicatorForCorrelationRules': return_dict})

otx_tools = [getIndicatorForIPv4,
             getIndicatorForIPv6,
             getIndicatorForDomain,
             getIndicatorForHostname,
             getIndicatorForFileHashes,
             getIndicatorForUrl,
             getIndicatorForCVE,
             getIndicatorForNIDS,
             getIndicatorForCorrelationRules]



### ### VirusTotal Nested and Parallel Calls

def get_random_object_from_list(list_of_objects):
    """

        This function selects and returns a random object from a list of objects. It is designed to handle any list length, including empty lists.

        Args:
        - list_of_objects: list, required, List containing objects from which the function will pick out a random object.
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'get_random_object_from_list': return_dict})

def get_first_object_from_list(list_of_objects):
    """

        Retrieves the first object from a given list. If the list is empty, it return `None`.

        Args:
        - list_of_objects: list, required, List containing objects from which the function will pick out the first object.
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'get_first_object_from_list': return_dict})

def calculate_sum_of_numbers(num1, num2):
    """

        Computes the sum of two numbers provided. Input numbers can be either integer or floating-point values.

        Args:
        - num1: Integer or Float, required, The first number
        - num2: Integer or Float, required, The second number
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'calculate_sum_of_numbers': return_dict})

def extract_resolution_date(dns_res_obj):
    """

        Extracts the date of DNS resolution from a DNS resolution object. The date is returned as a Unix timestamp.

        Args:
        - dns_res_obj: object, required, The DNS resolution object from which the date of resolution is to be extracted.
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'extract_resolution_date': return_dict})

def count_items_in_list(input_list):
    """

        This function takes a list as an input and returns the number of items present in the list.

        Args:
        - input_list: list, required, List whose items are to be counted
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'count_items_in_list': return_dict})

def vt_get_majority_vote(votes):
    """

        This function takes a dictionary of votes returns the name with the majority votes. If the votes are equal, it will return the first encountered key in the dictionary.

        Args:
        - votes: dictionary, required, dictionary of votes
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_majority_vote': return_dict})

def vt_get_multiple_domain_reports(domains, x_apikey):
    """

        retrieves reports for a list of domains provided. For each domain in the list, it requests the collected information regarding that domain from VirusTotal.

        Args:
        - domains: list of strings, required, A list of Domain names
        - x_apikey: string, required, Your API key
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_multiple_domain_reports': return_dict})

def vt_get_comments_on_multiple_domains(domains, x_apikey, limit=None, cursor=None):
    """

        This function will retrieve comments for each specified domain in the given list.

        Args:
        - domains, list of strings, required, List of domain names
        - x_apikey, string, required, Your API key
        - limit, int32, optional, Maximum number of comments to retrieve for each domain
        - cursor, string, optional, Continuation cursor
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_comments_on_multiple_domains': return_dict})

def vt_get_last_analysis_date_from_report(report):
    """

        This function retrieves the last analysis date from the domain report collected by VirusTotal. The returned date is in Unix timestamp format.

        Args:
        - report: dict, required, The domain report collected by vt_get_domain_report function.
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_last_analysis_date_from_report': return_dict})

def vt_is_date_within_range(timestamp, start=None, end=None):
    """

        Checks if a given Unix timestamp is within a specified date range. The range is specified by 'start' and 'end' dates formatted as 'YYYY/MM/DD'. It's permissible for only one of 'start' or 'end' to be present in the function call. If 'start' is not provided, the function checks if the timestamp is earlier than or equal to the 'end' date. Similarly, If 'end' is not provided, the function checks if the timestamp is later than or equal to the 'start' date.

        Args:
        - timestamp: int, required, Unix timestamp
        - start: string, optional, Start of the date range in 'YYYY/MM/DD' format
        - end: string, optional, End of the date range in 'YYYY/MM/DD' format
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_is_date_within_range': return_dict})

def convert_unix_timestamp_to_date(unix_timestamp):
    """

        Converts a UNIX timestamp to a human-readable date in the format 'YYYY/MM/DD'.

        Args:
        - unix_timestamp: integer, required, The UNIX timestamp to be converted.
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'convert_unix_timestamp_to_date': return_dict})

def vt_get_threat_actors_latest_modification_date(threat_actor_objects, x_apikey):
    """

        This function retrieves the latest modification date from a list of threat actor objects. It iterates through each threat actor object, checks its modification date, and returns the most recent modification date.

        Args:
        - threat_actor_objects: list of objects, required, A list of threat actor objects.
        - x_apikey: string, required, Your API key.
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_threat_actors_latest_modification_date': return_dict})

def vt_get_threat_actors_main_source_region(threat_actors, x_apikey):
    """

        This function takes a list of threat actor objects and returns the primary source region among them. Each threat actor object has an attribute 'source region', and the function analyses this attribute across all objects to determine and return the most common source region, deemed as the 'main' source region.

        Args:
        - threat_actors: list, required, List of threat actor objects
        - x_apikey: string, required, Your API key.
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_threat_actors_main_source_region': return_dict})

def vt_validate_historical_ssl_certificates(historical_ssl_certificates, x_apikey):
    """

        This function takes historical SSL certificates as input and checks if there is at least one valid SSL certificate present inside the provided historical data. It validates the SSL certificate by checking whether it is not expired and its issuing authority is trustworthy.

        Args:
        - historical_ssl_certificates: list, required, List of SSL certificates in the history
        - x_apikey: string, required, Your API key
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_validate_historical_ssl_certificates': return_dict})

def vt_get_dns_resolution_object(id, x_apikey):
    """

        This endpoint retrieves a Resolution object by its ID. A resolution object ID is made by appending the IP and the domain it resolves to together.

        Domain-IP resolutions. Resolution objects include the following attributes:
        date: <integer> date when the resolution was made (UTC timestamp).
        host_name: <string> domain or subdomain requested to the resolver.
        host_name_last_analysis_stats: <dictionary> last detection stats from the resolution's domain. Similar to the domains's last_analysis_stats attribute.
        ip_address: <string> IP address the domain was resolved to.
        ip_address_last_analysis_stats: <dictionary> last detection stats from the resolution's IP address. Similar to the IP address' last_analysis_stats attribute.
        resolver: <string> source of the resolution.

        Args:
        - id: string, required, Resolution object ID
        - x_apikey: string, required, Your API key

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_dns_resolution_object': return_dict})

def vt_get_objects_related_to_ip_address(ip, relationship, x_apikey, limit=None, cursor=None):
    """

        IP addresses have number of relationships to other objects. This returns ALL objects that fit the relationship.

        The relationships are documented here:
        - comments: The comments for the IP address. Returns a list of comments.
        - communicating_files: Files that communicate with the IP address. Returns a list of files.
        - downloaded_files: Files downloaded from the IP address. VT Enterprise users only. Returns a list of files.
        - graphs: Graphs including the IP address. Returns a list of graphs.
        - historical_ssl_certificates: SSL certificates associated with the IP. Returns a list of SSL certificates.
        - historical_whois: WHOIS information for the IP address. Retrurns a list of Whois attributes.
        - related_comments: Community posted comments in the IP's related objects. Returns a list of comments.
        - related_references: Returns the references related to the IP address. Returns a list of References.
        - related_threat_actors: Threat actors related to the IP address. Returns a list of threat actors.
        - referrer_files: Files containing the IP address. Returns a list of Files.
        - resolutions: Resolves the IP addresses. Returns a list of resolutions.
        - urls: Returns a list of URLs related to the IP address. Returns a list of URLs.

        Args:
        - ip, string, required, IP address
        - relationship, string, required, Relationship name (see the list of items from above)
        - x_apikey, string, required, Your API key
        - limit, int32, optional, Maximum number of comments to retrieve
        - cursor, string, optional, Continuation cursor

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_objects_related_to_ip_address': return_dict})

def vt_get_ip_address_report(ip, x_apikey):
    """

        Retrieve an IP address report. These reports condense all of the recent activity that VirusTotal has seen for the resource under consideration, as well as contextual information about it.
        This function specifically generates these reports using the IP address parameter.

        Args:
        - ip: string, required, IP address
        - x_apikey: string, required, Your API key

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_ip_address_report': return_dict})

def vt_add_votes_to_ip_address(ip, data, x_apikey):
    """

        With this function you can post a vote for a given file. The body for the POST request must be the JSON representation of a vote object. Note however that you don't need to provide an ID for the object, as they are automatically generated for new votes. The verdict attribute must have be either harmless or malicious.

        Please ensure that the JSON object you provide conforms accurately to valid JSON standards.

        Args:
        - ip, string, required, IP address
        - data, json, Vote object
        - x_apikey, string, required, Your API key

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_add_votes_to_ip_address': return_dict})

def vt_get_domain_report(domain, x_apikey):
    """

        Retrieves a domain report. These reports contain information regarding the domain itself that VirusTotal has collected.

        Args:
        - domain: string, required, Domain name
        - x_apikey: string, required, Your API key

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_domain_report': return_dict})

def vt_get_comments_on_ip_address(ip, x_apikey, limit=None, cursor=None):
    """

        Retrieves the comments on a provided IP address. Returns a list of Comment objects.

        Args:
        - ip, string, required, IP address
        - x_apikey, string, required, Your API key
        - limit, int32, optional, Maximum number of comments to retrieve
        - cursor, string, optional, Continuation cursor

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_comments_on_ip_address': return_dict})

def vt_add_comment_to_ip_address(ip, data, x_apikey):
    """

        With this function you can post a comment for a given IP address. The body for the POST request must be the JSON representation of a comment object. Notice however that you don't need to provide an ID for the object, as they are automatically generated for new comments.
        However, please note that you will need to provide a valid data JSON for using this function.

        Any word starting with # in your comment's text will be considered a tag, and added to the comment's tag attribute.

        Returns a Comment object.

        Args:
        - ip: string, required, IP address
        - data: json, required, A comment object
        - x_apikey: string, required, Your API key

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_add_comment_to_ip_address': return_dict})

def vt_get_object_descriptors_related_to_ip_address(ip, relationship, x_apikey, limit=None, cursor=None):
    """

        This specifically returns related object's IDs (and context attributes, if any). Please note that this will not return all attributes.

        You are expected to provide the relationship to the object you're interested in. The valid relationships are as follows.

        The relationships are documented here:
        - comments: The comments for the IP address.
        - communicating_files: Files that communicate with the IP address.
        - downloaded_files: Files downloaded from the IP address. VT Enterprise users only.
        - graphs: Graphs including the IP address.
        - historical_ssl_certificates: SSL certificates associated with the IP.
        - historical_whois: WHOIS information for the IP address. Retrurns a list of Whois attributes.
        - related_comments: Community posted comments in the IP's related objects.
        - related_references: Returns the references related to the IP address.
        - related_threat_actors: Threat actors related to the IP address.
        - referrer_files: Files containing the IP address.
        - resolutions: Resolves the IP addresses.
        - urls: Returns a list of URLs related to the IP address.

        Here are some useful descriptions of the arguments in this API, with the format - name of this argument: type of the data, required or optional, description of this argument.
        - ip: string, required, IP address
        - relationship: string, required, Relationship name (see table)
        - x_apikey: string, required, Your API key
        - limit: int32, optional, Maximum number of comments to retrieve
        - cursor: string, optional, Continuation cursor

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_object_descriptors_related_to_ip_address': return_dict})

def vt_get_objects_related_to_domain(domain, relationship, x_apikey, limit=None, cursor=None):
    """

        Objects are a key concept in the VirusTotal API. Each object has an identifier and a type.
        Each object has an associated URL, and each domain is associated with objects.
        This function returns ALL of the objects related to the domain, based on the specified relationship.

        The following describe the valid relationship:
        - caa_records: Records CAA for the domain.
        - cname_records: Records CNAME for the domain.
        - comments: Community posted comments about the domain.
        - communicating_files: Files that communicate with the domain.
        - downloaded_files: Files downloaded from that domain.
        - graphs: All graphs that include the domain.
        - historical_ssl_certificates: SSL certificates associated with the domain.
        - historical_whois: WHOIS information for the domain.
        - immediate_parent: Domain's immediate parent.
        - mx_records: Records MX for the domain.
        - ns_records: Records NS for the domain.
        - parent: Domain's top parent.
        - referrer_files: Refers to any and all files that contain this domain.
        - related_comments: Community posted comments in the domain's related objects.
        - related_references: Refers to the References related to the domain.
        - related_threat_actors: Refers to the threat actors related to the domain. A list of Threat Actors.
        - resolutions: DNS resolutions for the domain.
        - soa_records: Records SOA for the domain.
        - siblings: Refers to the Domain's sibling domains.
        - subdomains: Refers to the Domain's subdomains.
        - urls: Refers to the URLs that contain this domain.
        - user_votes: Refers to the current user's votes.


        Args:
        - domain: string, required, Domain name
        - relationship, string, required, Relationship name (see table)
        - x_apikey, string, required, Your API key
        - limit, int32, optional, Maximum number of comments to retrieve
        - cursor, string, optional, Continuation cursor

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_objects_related_to_domain': return_dict})

def vt_get_object_descriptors_related_to_domain(domain, relationship, x_apikey, limit=None, cursor=None):
    """

        This specifically returns related object's IDs (and context attributes, if any). Please note that this will not return all attributes. This will return objects relating to a domain.

        - caa_records: Records CAA for the domain.
        - cname_records: Records CNAME for the domain.
        - comments: Community posted comments about the domain.
        - communicating_files: Files that communicate with the domain.
        - downloaded_files: Files downloaded from that domain.
        - graphs: All graphs that include the domain.
        - historical_ssl_certificates: SSL certificates associated with the domain.
        - historical_whois: WHOIS information for the domain.
        - immediate_parent: Domain's immediate parent.
        - mx_records: Records MX for the domain.
        - ns_records: Records NS for the domain.
        - parent: Domain's top parent.
        - referrer_files: Refers to any and all files that contain this domain.
        - related_comments: Community posted comments in the domain's related objects.
        - related_references: Refers to the References related to the domain.
        - related_threat_actors: Refers to the threat actors related to the domain. A list of Threat Actors.
        - resolutions: DNS resolutions for the domain.
        - soa_records: Records SOA for the domain.
        - siblings: Refers to the Domain's sibling domains.
        - subdomains: Refers to the Domain's subdomains.
        - urls: Refers to the URLs that contain this domain.
        - user_votes: Refers to the current user's votes.

        Args:
        - domain: string, required, Domain name
        - relationship: string, required, Relationship name (see table)
        - x_apikey: string, required, Your API key
        - limit: int32, optional, Maximum number of comments to retrieve
        - cursor: string, optional, Continuation cursor

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_object_descriptors_related_to_domain': return_dict})

def vt_get_comments_on_domain(domain, x_apikey, limit=None, cursor=None):
    """

    This function will retrieve comments on a specified domain.

    Args:
    - domain, string, required, Domain name
    - x_apikey, string, required, Your API key
    - limit, int32, optional, Maximum number of comments to retrieve
    - cursor, string, optional, Continuation cursor
    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_comments_on_domain': return_dict})

def vt_get_votes_on_ip_address(ip):
    """

        This function will retrieve votes on a provided IP address.

        Args:
        - ip: string, required, ip address

    """
    args_dict = locals()
    return_dict = {}
    for key, value in args_dict.items():
        if value:
            return_dict[key] = value
    correctness.append({'vt_get_votes_on_ip_address': return_dict})

vt_multi_tools = [get_random_object_from_list, 
                    get_first_object_from_list, 
                    calculate_sum_of_numbers, 
                    extract_resolution_date, 
                    count_items_in_list, 
                    vt_get_majority_vote, 
                    vt_get_multiple_domain_reports, 
                    vt_get_comments_on_multiple_domains, 
                    vt_get_last_analysis_date_from_report, 
                    vt_is_date_within_range, 
                    convert_unix_timestamp_to_date, 
                    vt_get_threat_actors_latest_modification_date, 
                    vt_get_threat_actors_main_source_region, 
                    vt_validate_historical_ssl_certificates, 
                    vt_get_dns_resolution_object, 
                    vt_get_objects_related_to_ip_address, 
                    vt_get_ip_address_report, 
                    vt_add_votes_to_ip_address, 
                    vt_get_domain_report, 
                    vt_get_comments_on_ip_address, 
                    vt_add_comment_to_ip_address, 
                    vt_get_object_descriptors_related_to_ip_address, 
                    vt_get_objects_related_to_domain, 
                    vt_get_object_descriptors_related_to_domain, 
                    vt_get_comments_on_domain, 
                    vt_get_votes_on_ip_address]




### CVECPE Nested

def count_cvecpe_items(cvecpeList):
    """
    This function counts the total number of CVE and CPE items provided in the arg.

    Args:
    - cvecpeList: This arg takes in a list of CVE or CPE items.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"count_cvecpe_items": return_dict})

def summarize_cvecpes(cvecpeList):
    """
    This function can summarize the contents of provided CVE or CPE items.

    Args:
    - cvecpeList: This arg takes in a list of CVE or CPE items.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"summarize_cvecpes": return_dict})

def verify_and_process_data_range_start(startdate, enddate):
    """
    This function can verify whether the range of dates being searched is within 3 months. If true, it returns the original startdate. If not, it will automatically truncate and return an appropriate startdate resulting in a 3-month time span. Note that searchCVE or searchCPE cannot handle time span longer than 3 months.

    Args:
    - startdate: The start date of the searched time span.
    - enddate: The end date of the searched time span.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"verify_and_process_data_range_start": return_dict})

def verify_and_process_data_range_end(startdate, enddate):
    """
    This function can verify whether the range of dates being searched is within 3 months. If true, it returns the original enddate. If not, it will automatically truncate and return an appropriate enddate resulting in a 3-month time span. Note that searchCVE or searchCPE cannot handle time span longer than 3 months.

    Args:
    - startdate: The start date of the searched time span.
    - enddate: The end date of the searched time span.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"verify_and_process_data_range_end": return_dict})

def compare_cvecpes(cvecpeList1, cvecpeList2):
    """
    This function can compare the contents of two lists of provided CVE or CPE items, summarizing the common parts and differences between the two lists.

    Args:
    - cvecpeList1: This arg takes in a list of CVE or CPE items to compare with another list.
    - cvecpeList2: This arg takes in a list of CVE or CPE items to compare with another list.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"compare_cvecpes": return_dict})

def search_backup_keywords(cvecpeList, backup_keyword):
    """
    This function takes in a backup keyword and a list of CVE or CPE items found by an initial searchCVE or searchCPE. If the list is empty, the function will search again using the backup keyword instead of the original keyword. If it is not empty, the function returns the original searched results.

    Args:
    - cvecpeList: This arg takes in a list of CVE or CPE items.
    - backup_keyword: The backup keyword to search if the original keyword doesn't lead to corresponding results.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"search_backup_keywords": return_dict})

def getCPEName(cpeObject):
    """
    This function takes a CPE object and extracts the CPE name.

    Args:
    - cpeObject: A CPE object from which the CPE name is to be extracted. The object should have a 'cpeName' field.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"getCPEName": return_dict})

def get_first_object_from_list(list_of_objects):
    """
    Retrieves the first object from a given list. If the list is empty, it return `None`.

    Args:
    - list_of_objects: List containing objects.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"get_first_object_from_list": return_dict})

def countCVEsBySeverity(cve_list):
    """
    Analyze a list of CVE objects, and return a dictionary with counts of CVEs according to their 'cvssV3Severity' (LOW, MEDIUM, HIGH, CRITICAL).

    Args:
    - cve_list: A list of dictionary objects each representing a CVE. Each dictionary should include a 'cvssV3Severity' key.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"countCVEsBySeverity": return_dict})

def sortCVEsByCVSSv3Score(cve_list, descending=True):
    """
    Accepts a list of CVE objects and sorts them by their CVSS Version 3.x base scores. If a CVE object does not contain a CVSS v3 score, it is assumed to have the lowest possible score (i.e., 0).

    Args:
    - cve_list: List of CVE objects, where each object contains details such as CVE identifier, CVSS v2 and v3 scores, etc.
    - descending: If set to True, the list will be sorted in descending order (highest CVSSv3Score first).
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"sortCVEsByCVSSv3Score": return_dict})

def sortCVEsByCVSSv2Score(cve_list, descending=True):
    """
    Accepts a list of CVE objects and sorts them by their CVSS Version 2.0 base scores. If a CVE object does not contain a CVSS v2 score, it is assumed to have the lowest possible score (i.e., 0).

    Args:
    - cve_list: List of CVE objects, where each object contains details such as CVE identifier, CVSS v2 and v3 scores, etc.
    - descending: If set to True, the list will be sorted in descending order (highest CVSSv2Score first). Defaults to True.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"sortCVEsByCVSSv2Score": return_dict})

def sortCVEsByModDate(cve_list, descending=True):
    """
    This function sorts a list of CVE objects by their last modification date.

    Args:
    - cve_list: A list of CVE objects. Each object should at least have a property for last modification date.
    - descending: If set to True, the list will be sorted in descending order (most recently modified first).
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"sortCVEsByModDate": return_dict})

def filterCVEByLanguage(cve_list, language):
    """
    Filters a collection of CVE (Common Vulnerabilities and Exposures) objects and returns a list of the ones that have descriptions for a specific language.

    Args:
    - cve_list: A list of CVE objects. Each object should contain information about a particular CVE, including its description available in various languages.
    - language: Language code for which the function will check in the description field of the CVE objects. This must follow the ISO 639-1 language codes, such as 'en' for English, 'es' for Spanish, and 'de' for German, etc.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"filterCVEByLanguage": return_dict})

def filterCVEsBySeverity(cveList, severityLevel):
    """
    Returns a list of CVE objects from the given collection that have the provided severity level.

    Args:
    - cveList: List of objects containing a collection of CVEs. Each CVE object is expected to have 'cvssV2Severity' and/or 'cvssV3Severity' properties reflecting the severity level of the vulnerability.
    - severityLevel: The severity level with which to filter the CVEs. Accepts 'LOW', 'MEDIUM', 'HIGH' for both 'cvssV2Severity' and 'cvssV3Severity', and 'CRITICAL' for 'cvssV3Severity' only.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"filterCVEsBySeverity": return_dict})

def filterDeprecatedCPEs(cpeList):
    """
    Loop through the CPE objects in the list and return the ones that are not deprecated.

    Args:
    - cpeList: A list of CPE objects. Each CPE object in the list has a 'deprecated' key. If the value of this key is False, it means the CPE object is not deprecated.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"filterDeprecatedCPEs": return_dict})

def sortCPEsByLastMod(cpeList, descending=True):
    """
    Sorts a list of object collections of CPEs by their last modification time.

    Args:
    - cpeList: The list of object collections of CPEs that need to be sorted. Each object collection has a lastModified field.
    - descending: Determines the order of sort. If True, CPEs will be sorted in descending order of 'last modification time'. If False, the sorting will be in descending order.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"sortCPEsByLastMod": return_dict})

def mergeCVEs(list1, list2):
    """
    This function takes two lists of objects each containing a collection of CVEs, and combines them into a single list.

    Args:
    - list1: First list of objects each holding details of a CVE. Defined by NVD format.
    - list2: Second list of objects each holding details of a CVE. Defined by NVD format.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"mergeCVEs": return_dict})

def mergeCPEs(list1, list2):
    """
    Combines two lists of CPEs into one.

    Args:
    - list1: List of CPEs. Each object in the list should contain a collection of CPEs.
    - list2: Another list of CPEs. Each object in this list should also contain a collection of CPEs.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"mergeCPEs": return_dict})

def searchCVE(cpeName=None, cveId=None, cvssV2Metrics=None, cvssV2Severity=None, cvssV3Metrics=None, cvssV3Severity=None, cweId=None, hasCertAlerts=None, hasCertNotes=None, hasOval=None, isVulnerable=None, keywordExactMatch=None, keywordSearch=None, lastModStartDate=None, lastModEndDate=None, noRejected=None, pubStartDate=None, pubEndDate=None, sourceIdentifier=None, versionEnd=None, versionEndType=None, versionStart=None, versionStartType=None, virtualMatchString=None, limit=None, delay=None, key=None, verbose=None):
    """
    NVDLib is a Python API wrapper utilizing the REST API provided by NIST for the National Vulnerability Database (NVD). NVDLib CVESearch can search specific CVEs according to the uses requests.

    Args:
    - cpeName: This value will be compared against the CPE Match Criteria within a CVE applicability statement. Partial match strings are allowed.
    - cveId: Returns a single CVE that already exists in the NVD.
    - cvssV2Metrics: This parameter returns only the CVEs that match the provided CVSSv2 vector string. Either full or partial vector strings may be used. This parameter cannot be used in requests that include cvssV3Metrics.
    - cvssV2Severity: Find vulnerabilities having a 'LOW', 'MEDIUM', or 'HIGH' version 2 severity.
    - cvssV3Metrics: This parameter returns only the CVEs that match the provided CVSSv3 vector string. Either full or partial vector strings may be used. This parameter cannot be used in requests that include cvssV2Metrics.                                                                                                                                                          - cvssV3Severity: Find vulnerabilities having a 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL' version 3 severity.
    - cweId: Filter collection by CWE (Common Weakness Enumeration) ID. A CVE can have multiple CWE IDs assigned to it.
    - hasCertAlerts: Returns CVE that contain a Technical Alert from US-CERT.
    - hasCertNotes: Returns CVE that contain a Vulnerability Note from CERT/CC.
    - hasOval: Returns CVE that contain information from MITRE's Open Vulnerability and Assessment Language (OVAL) before this transitioned to the Center for Internet Security (CIS).
    - isVulnerable: Returns CVE associated with a specific CPE, where the CPE is also considered vulnerable. REQUIRES cpeName parameter. isVulnerable is not compatible with virtualMatchString parameter.
    - keywordExactMatch: When keywordSearch is used along with keywordExactmatch, it will search the NVD for CVEs containing exactly what was passed to keywordSearch. REQUIRES keywordSearch.
    - keywordSearch: Searches CVEs where a word or phrase is found in the current description. If passing multiple keywords with a space character in between then each word must exist somewhere in the description, not necessarily together unless keywordExactMatch=True is passed to searchCVE.
    - lastModStartDate: This argument has a str with datetime format. These parameters return only the CVEs that were last modified during the specified period. If a CVE has been modified more recently than the specified period, it will not be included in the response. If filtering by the last modified date, both lastModStartDate and lastModEndDate are REQUIRED. The maximum allowable range when using any date range parameters is 120 consecutive days.
    - lastModEndDate: This argument has a str with datetime format. Required if using lastModStartDate.
    - noRejected: Filters out all CVEs that are in a reject or rejected status. Searches without this parameter include rejected CVEs.
    - pubStartDate: This argument has a str with datetime format. These parameters return only the CVEs that were added to the NVD during the specified period. If filtering by the published date, both pubStartDate and pubEndDate are REQUIRED. The maximum allowable range when using any date range parameters is 120 consecutive days.
    - pubEndDate: This argument has a str with datetime format. Required if using pubStartDate.
    - sourceIdentifier: Returns CVE where the data source of the CVE is the value that is passed to sourceIdentifier.
    - versionEnd: Must be combined with versionEndType and virtualMatchString. Returns only the CVEs associated with CPEs in specific version ranges.
    - versionEndType: Must be combined with versionEnd and virtualMatchString. Valid values are including or excluding. Denotes to include the specified version in versionEnd, or exclude it.
    - versionStart: Must be combined with versionStartType and virtualMatchString. Returns only CVEs with specific versions. Requests that include versionStart cannot include a version component in the virtualMatchString.
    - versionStartType: Must be combined with versionStart and virtualMatchString. Valid values are including or excluding. Denotes to include the specified version in versionStart, or exclude it.
    - virtualMatchString: A more broad filter compared to cpeName. The cpe match string that is passed to virtualMatchString is compared against the CPE Match Criteria present on CVE applicability statements.
    - limit: Custom argument to limit the number of results of the search. Allowed any number between 1 and 2000.
    - delay: Can only be used if an API key is provided. This allows the user to define a delay. The delay must be greater than 0.6 seconds. The NVD API recommends scripts sleep for at last 6 seconds in between requests.
    - key: NVD API Key. Allows for the user to define a delay. NVD recommends scripts sleep 6 seconds in between requests. If no valid API key is provided, requests are sent with a 6 second delay.
    - verbose: Prints the full NVD API URL for each request.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"searchCVE": return_dict})

def searchCPE(cpeNameId=None, cpeMatchString=None, keywordExactMatch=None, keywordSearch=None, lastModStartDate=None, lastModEndDate=None, limit=None, key=None, delay=6, verbose=None):
    """
    NVDLib is a Python API wrapper utilizing the REST API provided by NIST for the National Vulnerability Database (NVD). Searching for CPEs is similar to searching for CVEs albeit less parameters. CPE match strings are allowed, meaning if partial strings are known, you can search for all possible CPE names. Like searching CVEs, the parameters are not positional.

    Args:
    - cpeNameId: Returns a specific CPE record using its UUID. If a correctly formatted UUID is passed but it does not exist, it will return empty results. The UUID is the cpeNameId value when searching CPE.
    - cpeMatchString: Use a partial CPE name to search for other CPE names.
    - keywordExactMatch: Searches metadata within CPE title and reference links for an exact match of the phrase or word passed to it. Must be included with keywordSearch.
    - keywordSearch: Returns CPE records where a word or phrase is found in the metadata title or reference links. Space characters act as an AND statement.
    - lastModStartDate: CPE last modification start date. Maximum 120 day range. A start and end date is required. All times are in UTC 00:00. A datetime object or string can be passed as a date. NVDLib will automatically parse the datetime object into the correct format. String Example: "2020-06-28 00:00"
    - lastModEndDate: CPE last modification end date. Maximum 120 day range. Must be included with lastModStartDate. Example: "2020-06-28 00:00"
    - limit: Limits the number of results of the search.
    - key: NVD API Key. Allows for a request every 0.6 seconds instead of 6 seconds.
    - delay: Can only be used if an API key is provided. The amount of time to sleep in between requests. Must be a value above 0.6 seconds if an API key is present. delay is set to 6 seconds if no API key is passed.
    - verbose: Prints the URL request for debugging purposes.
    """
    args_dict = locals()
    args_dict.pop("kwargs", None)  # Remove kwargs if it exists
    return_dict = {}
    for key, value in args_dict.items():
        if value:
          return_dict[key] = value
    correctness.append({"searchCPE": return_dict})

nvdmulti_tools = [count_cvecpe_items, 
         summarize_cvecpes, 
         verify_and_process_data_range_start, 
         verify_and_process_data_range_end, 
         compare_cvecpes, 
         search_backup_keywords, 
         getCPEName, 
         get_first_object_from_list, 
         countCVEsBySeverity, 
         sortCVEsByCVSSv3Score, 
         sortCVEsByCVSSv2Score, 
         sortCVEsByModDate, 
         filterCVEByLanguage, 
         filterCVEsBySeverity, 
         filterDeprecatedCPEs, 
         sortCPEsByLastMod, 
         mergeCVEs, 
         mergeCPEs, 
         searchCVE, 
         searchCPE]



# #below are the functions for the prompt way
# from openai import OpenAI

# OPENAI_PROMPT =\
# """
# You are given multiple functions and a user query.

# Please proceed with generating a function call for the function with the proper arguments that best answers the given prompt.

# Respond with nothing but the function call ONLY, such that I can directly execute your function call without any post processing necessary from my end. Do not use variables.

# {tools}

# Question: {input}
# """


# def construct_tool_descriptions(tools):
#     prompt = ""
#     for tool in tools:
#         # 获取函数签名
#         func_signature = str(inspect.signature(tool))
#         func_name = tool.__name__
#         # 获取函数文档字符串
#         func_docstring = tool.__doc__ or "No documentation provided."
        
#         # 构建最终的函数描述
#         prompt += f"Function:\ndef {func_name}{func_signature}:\n" + "\"\"\"\n" + f"{func_docstring}" + "\n\"\"\"\n"
#     return prompt

# def query_openai(prompt, model_name):
#   client = OpenAI()
#   response = client.chat.completions.create(model= model_name,
#                                              messages=[{"role" : "user", "content" : prompt}])
#   return response.choices[0].message.content


# def construct_prompt_and_call_model_openai(sample, task_prompt, model_name):
#     prompt = OPENAI_PROMPT.format(tools=task_prompt, input=sample.Input)
#     call = query_openai(prompt, model_name)
#     return call


