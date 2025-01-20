import openreview
import re
from typing import Union, List
import os
import requests

client = openreview.api.OpenReviewClient(
    baseurl='https://api2.openreview.net',
    username='*********',
    password='*********'
)

def get_submissions(client, venue_id, status='all'):
    # Retrieve the venue group information
    venue_group = client.get_group(venue_id)

    # Define the mapping of status to the respective content field
    status_mapping = {
        "all": venue_group.content['submission_name']['value'],
        "accepted": venue_group.id,  # Assuming 'accepted' status doesn't have a direct field
        "under_review": venue_group.content['submission_venue_id']['value'],
        "withdrawn": venue_group.content['withdrawn_venue_id']['value'],
        "desk_rejected": venue_group.content['desk_rejected_venue_id']['value']
    }
    # Fetch the corresponding submission invitation or venue ID
    if status in status_mapping:
        if status == "all":
            # Return all submissions regardless of their status
            return client.get_all_notes(invitation=f'{venue_id}/-/{status_mapping[status]}')
        # For all other statuses, use the content field 'venueid'
        return client.get_all_notes(content={'venueid': status_mapping[status]})
    raise ValueError(f"Invalid status: {status}. Valid options are: {list(status_mapping.keys())}")


def contains_text(submission: dict, target_text: str, fields: Union[str, List[str]] = ['title', 'abstract'],
                  is_regex: bool = False) -> bool:
    # If 'all', consider all available keys in the submission for matching
    if fields == 'all':
        fields = ['title', 'abstract', 'keywords', 'primary_area', 'TLDR']

    # Convert string input for fields into a list
    if isinstance(fields, str):
        fields = [fields]

    # Iterate over the specified fields
    for field in fields:
        content = submission.get(field, "")

        # Join lists into a single string (e.g., keywords)
        if isinstance(content, list):
            content = " ".join(content)

        # Check if the target_text is found in the content of the field
        if is_regex:
            if re.search(target_text, content, re.IGNORECASE):
                return True
        else:
            if target_text in content:
                return True

    # If no matches were found, return False
    return False

from datetime import datetime

def extract_submission_info(submission):
    # Helper function to convert timestamps to datetime
    def convert_timestamp_to_date(timestamp):
        return datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d') if timestamp else None

    # Extract the required information
    submission_info = {
        'id': submission.id,
        'title': submission.content['title']['value'],
        'abstract': submission.content['abstract']['value'],
        'keywords': submission.content['keywords']['value'],
        'primary_area': submission.content['primary_area']['value'],
        'TLDR': submission.content['TLDR']['value'] if 'TLDR' in submission.content else "",
        'creation_date': convert_timestamp_to_date(submission.cdate),
        'original_date': convert_timestamp_to_date(submission.odate),
        'modification_date': convert_timestamp_to_date(submission.mdate),
        'forum_link': f"https://openreview.net/forum?id={submission.id}",
        'pdf_link': f"https://openreview.net/pdf?id={submission.id}"
    }
    return submission_info


def search_submissions(submissions: List, target_text: str, fields: Union[str, List[str]] = ['title', 'abstract'],
                       is_regex: bool = False) -> List:
    matching_submissions = []

    for submission in submissions:
        if contains_text(submission, target_text, fields, is_regex):
            matching_submissions.append(submission)

    return matching_submissions

def sanitize_file_name(file_name):
    return re.sub(r'[<>:"/\\|?*\.,]', '', file_name)

def download_pdf(url, save_folder, file_name=None):
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)


    if not file_name:
        file_name = url.split('/')[-1]
        if not file_name.endswith('.pdf'):
            file_name += '.pdf'
    file_name = sanitize_file_name(file_name)

    file_path = os.path.join(save_folder, file_name)

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()


        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        print(f"PDF 已成功下载并保存到: {file_path}")

    except requests.exceptions.RequestException as e:
        print(f"下载失败: {e}")



# pdf_url = "https://arxiv.org/pdf/2301.00101.pdf"
# save_directory = "./pdf_files"
# download_pdf(pdf_url, save_directory)

venue_id = 'ICLR.cc/2025/Conference'
submissions = get_submissions(client, venue_id)
# submissions = get_submissions(client, venue_id, 'under_review')
submission_infos = [extract_submission_info(sub) for sub in submissions]

langs = ['reinforcement learning', 'safe']
# lang_regex = '|'.join(langs)
lang_regex = ''.join(f"(?=.*{word})" for word in langs)
matching_submissions = search_submissions(submission_infos, lang_regex, is_regex=True, fields='all')
for mat in matching_submissions:
    # print(mat['title'])
    folder = './ICLR2025_SafeRL'
    download_pdf( mat['pdf_link'], folder, mat['title'])
