#!/usr/bin/python

from oAuth4Devices import check_authentication, get_authenticated_http
from apiclient import errors
from apiclient.http import MediaFileUpload
import mimetypes


def debug(value):
    print value


class Delivery(object):
    def __init__(self, http):
        from apiclient.discovery import build

        self.service = build("drive", "v2", http=http)

    @classmethod
    def compute_md5(cls, file_path):
        import hashlib
        return hashlib.md5(open(file_path, 'r').read()).hexdigest()


    def find_id(self, parent_id, folder):
        page_token = None
        #Now find the correct child name
        file_list = {}
        while True:
            #List all the remote files from this directory
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token
                children = self.service.children().list(folderId=parent_id, **param).execute()

                for child in children.get('items', []):
                    child_info = self.service.files().get(fileId=child['id']).execute()
                    print "Found '%s'" % child_info['title']
                    if folder == child_info['title']:
                        return child['id']

                page_token = children.get('nextPageToken')
                if not page_token:
                    break
            except errors.HttpError, error:
                print 'An error occurred: %s' % error
                break

        raise Exception("Remote id not found %s" % folder)

    def list_files(self, remote_id):
        page_token = None
        #Now find the correct child name
        file_list = {}
        while True:
            #List all the remote files from this directory
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token
                children = self.service.children().list(folderId=remote_id, **param).execute()

                for child in children.get('items', []):
                    child_info = self.service.files().get(fileId=child['id']).execute()
                    print "Found '%s'" % child_info['title']
                    file_list[child_info['title']] = child_info
                page_token = children.get('nextPageToken')
                if not page_token:
                    break
            except errors.HttpError, error:
                print 'An error occurred: %s' % error
                break

        return file_list


    def make_delivery_rom(self, local_rom_path, dest_folder, remote_rom_name):
        import os.path
        self.make_delivery(local_rom_path, os.path.join(dest_folder, "rom"), remote_rom_name)


    def start_async_upload(self, file_body, r_file):
        import threading

        class AsyncUpload(threading.Thread):
            def __init__(self, delivery, body, r_file):
                super(AsyncUpload, self).__init__()
                self.delivery   = delivery
                self.body       = body
                self.r_file     = r_file

            def run(self):
                self.delivery.service.files().update(fileId=self.r_file['id'],
                                            body=self.r_file,
                                            media_body=self.body).execute()

        upload = AsyncUpload(self, file_body, r_file)
        upload.start()
        return upload

    def make_delivery(self, local_file_path, dest_folder, remote_file_name):
        #Get Root folder
        about = self.service.about().get().execute()
        remote_id = about["rootFolderId"]

        folder_list = dest_folder.split("/")
        for f in folder_list:
            remote_id = self.find_id(remote_id, f)

        #Now that we've got the correct remote_id for the folder we can browse it to retrieve latest version available
        children = self.list_files(remote_id)

        for child in children:
            assert(child != remote_file_name)


        new_file = {}
        new_file['title'] = remote_file_name
        new_file['parents'] = [{"id":remote_id}]
        new_file['mimeType'] = mimetypes.guess_type(local_file_path)[0]

        #First of all create the file
        r_file = self.service.files().insert(body=new_file,
                media_body=None).execute()


        media_body = MediaFileUpload(local_file_path,
                mimetype=r_file['mimeType'], resumable=True)


        upload_thread = self.start_async_upload(media_body, r_file)
        import time
        time.sleep(1)
        while media_body.progress is None:
            print "Waiting for upload to start"

        while media_body.progress.progress() < 1:
            time.sleep(1)
            print "current progress %s" % int(media_body.progress.progress()
                        * 100)
        upload_thread.join()

if __name__ == "__main__":
    result = check_authentication()
    http = get_authenticated_http(result)

    delivery = Delivery(http)
    delivery.make_delivery_rom("/home/blegrand/android/jb/out/target/product/es209ra/cm-10-20121220-UNOFFICIAL-es209ra.zip", "AndroidRelease", "cm10.test.zip")

