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
            assert(child['title'] != remote_file_name) 


        new_file = {}
        new_file['title'] = remote_file_name
        new_file['parents'] = [{"id":remote_id}]
        new_file['mimeType'] = mimetypes.guess_type(local_file_path)[0]

        #First of all create the file
        r_file = self.service.files().insert(body=new_file,
                media_body=None).execute()
        #TODO compare the checksums
        md5 = self.compute_md5(local_file_path)
        r_md5 = r_file['md5Checksum']


        media_body = MediaFileUpload(local_file_path,
                mimetype=r_file['mimeType'], resumable=True)

        if md5 != r_md5:

            debug(md5)
            debug(local_file_path)
            debug(r_file['md5Checksum'])

            #TODO UPDATE
            r_file = self.service.files().update(fileId=r_file['id'],
                                            body=r_file,
                                            media_body=media_body).execute()
        else:
            #The md5 are egals do not update
            pass


if __name__ == "__main__":
    result = check_authentication()
    http = get_authenticated_http(result)

    delivery = Delivery(http)
    delivery.make_delivery_rom("/home/benjamin/android/unzipped_roms/cm-9-20121127-UNOFFICIAL-es209ra-hwa.zip", "AndroidRelease", "cm9.test.zip")    

