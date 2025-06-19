import os
import sys
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import rag.maintain_vectordb as vdb
import utils.data_utils as dut
import src.config as cfg
from src.scrape import get_all_pdf_links, download_pdfs

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv(override=True)
service_account_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))

creds = service_account.Credentials.from_service_account_info(
    service_account_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
)
drive_service = build("drive", "v3", credentials=creds)

curr_dir = os.path.dirname(__file__)
RAG_DIR = os.path.join(curr_dir, "..", "rag")

# --- Mapping of exportable Google MIME types ---
EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": "application/pdf",  # Google Docs
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Excel
    "application/vnd.google-apps.presentation": "application/pdf",  # Slides
    "application/vnd.google-apps.drawing": "image/png",
}

FILE_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/csv": ".csv",
    "image/png": ".png",
}


# Extract folder ID
def extract_folder_id(data_source):
    import re

    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", data_source)
    return match.group(1) if match else None


# List files in the folder
def download_files_from_google_drive_folder(data_source, downloads_folder):
    folder_id = extract_folder_id(data_source)
    results = (
        drive_service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType)",
        )
        .execute()
    )
    files = results.get("files", [])

    os.makedirs(downloads_folder, exist_ok=True)

    # filepaths = []
    for f in files:
        file_id = f["id"]
        filename = f["name"]
        print(f"file_id: {file_id}, name: {filename}")

        file_metadata = drive_service.files().get(fileId=file_id).execute()
        mime_type = file_metadata["mimeType"]
        if mime_type.startswith("application/vnd.google-apps"):
            # Google-native file — export it
            export_mime = EXPORT_MIME_TYPES.get(mime_type, "application/pdf")
            request = drive_service.files().export_media(
                fileId=file_id, mimeType=export_mime
            )

            # Use extension if not already in filename
            extension = FILE_EXTENSIONS.get(export_mime, "")
            if not filename.lower().endswith(extension):
                filename += extension

            print(f"Exporting '{file_metadata['name']}' as {export_mime}")
        else:
            # Binary file — download it directly
            request = drive_service.files().get_media(fileId=file_id)
            print(f"Downloading binary file '{file_metadata['name']}'")

        fh = open(f"{downloads_folder}/{filename}", "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download progress: {int(status.progress() * 100)}%")
        # filepaths.append(f"{downloads_folder}/{name}")

    print(f"Downloaded all files to {downloads_folder}")


if __name__ == "__main__":
    print("Arguments received:", sys.argv[1])

    inputs = json.loads(sys.argv[1])
    print(inputs)

    dirname = os.path.join(cfg.RESULTS_DIR, inputs["vectordb_collection_name"])

    # create the dir if it doesn't exist
    dut.create_dir_if_doesnt_exist(dirname)

    if not os.path.exists(os.path.join(dirname, "embedded_sources.csv")):
        dut.create_csv_with_headers(
            dirname=dirname, filename="embedded_sources.csv", headers=["Sources"]
        )

    # 5. Embed the documents in the vector DB
    data_source = inputs["data_source"]
    data_to_add = None
    temp_downloads_folder = None

    if not data_source.startswith("http"):
        # local folder link
        data_to_add = os.listdir(data_source)
    elif "drive.google" in data_source:
        # Google drive folder link
        temp_downloads_folder = os.path.join(dirname, "temp")
        download_files_from_google_drive_folder(data_source, temp_downloads_folder)
        data_to_add = os.listdir(temp_downloads_folder)
    else:
        # web link to some webpage
        temp_downloads_folder = os.path.join(dirname, "temp")
        pdf_links = get_all_pdf_links(data_source)
        print(f"Found {len(pdf_links)} PDFs:")
        for link in pdf_links:
            print(link)
        download_pdfs(pdf_links, temp_downloads_folder)
        data_to_add = os.listdir(temp_downloads_folder)

    print(f"Data to add: {data_to_add}")

    # vdb.add_update_docs(
    #     data_to_add=data_to_add,
    #     collection_name=inputs["vectordb_collection_name"],
    #     addnl_metadata={
    #         "source_type": "link",
    #     },
    #     dir_name=temp_downloads_folder,
    #     update=False,
    # )

    # if temp_downloads_folder:
    #     print("Deleting the downloads folder now.")
    #     shutil.rmtree(temp_downloads_folder)
