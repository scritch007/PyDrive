#Handle File information
import os
#from logging import debug
from apiclient import errors
import mimetypes
from apiclient.http import MediaFileUpload

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

def debug(value):
    print value

class File(object):
    """
    Class to handle backup and sync

    Sync only works as a backup of the local folder.
    """

    def __init__(self, http):
        """
        requires and authenticated http request. This will sync to the
        destination folder
        """
        from apiclient.discovery import build

        self.service = build('drive', 'v2', http=http)

    @classmethod
    def is_folder(cls, file_dict):
        return file_dict['mimeType'] == FOLDER_MIME_TYPE

    @classmethod
    def compute_md5(cls, file_path):
        import hashlib
        return hashlib.md5(open(file_path, 'r').read()).hexdigest()


    def sync(self, local_folder, g_drive_folder_id=None, dest_folder=None):
        """
        Sync the local_folder to the cloud, using the dest_folder as root folder

        if g_drive_folder_id is provided we will use this one as destination

        if dest_folder is None it will use the / folder from gdrive

        Currently dest_folder doesn't work

        When a file has twice the same name remotely this is not handled
        properly !!!!
        """

        #First browse the files remotely
        if dest_folder is not None:
            raise Exception("Feature currently not available")

        if g_drive_folder_id is None and dest_folder is None:
            #Use the / folder
            about = self.service.about().get().execute()
            g_drive_folder_id = about["rootFolderId"]
        page_token = None

        file_list = {}
        while True:
            #List all the remote files from this directory
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token
                children = self.service.children().list(folderId=g_drive_folder_id, **param).execute()

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


        child_folders = []

        debug("Browsing folder %s" % local_folder)
        for f in os.listdir(local_folder):
            file_full_path = os.path.join(local_folder, f)
            if os.path.isdir(file_full_path):

                folder = file_list.get(f, None)
                if folder is not None:
                    if not self.is_folder(folder):
                        #TODO the file exists but is now a folder and was previously
                        #a file
                        self.service.files().trash(folder["id"]).execute()
                    else:

                        child_folders.append(folder)
                        continue


                #TODO create a new folder
                new_folder = {}
                new_folder['title'] = f
                new_folder['parents'] = [{"id":g_drive_folder_id}]
                new_folder['mimeType'] = FOLDER_MIME_TYPE

                new_folder = self.service.files().insert(body=new_folder, media_body=None).execute()


                child_folders.append(new_folder)
            else:
                r_file = file_list.get(f, None)
                if r_file is None:
                    #TODO update file
                    new_file = {}
                    new_file['title'] = f
                    new_file['parents'] = [{"id":g_drive_folder_id}]
                    new_file['mimeType'] = mimetypes.guess_type(f)[0]

                    #First of all create the file
                    r_file = self.service.files().insert(body=new_file,
                            media_body=None).execute()
                #Compare the Checksums
                if self.is_folder(r_file):
                    #TODO the remote is a folder but local is a file
                    continue
                else:
                    #TODO compare the checksums
                    md5 = self.compute_md5(file_full_path)
                    r_md5 = r_file['md5Checksum']


                    media_body = MediaFileUpload(file_full_path,
                            mimetype=r_file['mimeType'], resumable=True)
                    if md5 != r_md5:

                        debug(md5)
                        debug(file_full_path)
                        debug(r_file['md5Checksum'])

                        #TODO UPDATE
                        r_file = self.service.files().update(fileId=r_file['id'],
                                                        body=r_file,
                                                        media_body=media_body).execute()
                    else:
                        #The md5 are egals do not update
                        pass

        for child in child_folders:
            #Now sync the subfolders
            child_path = os.path.join(local_folder, child['title'])
            print "syncing %s"  % child_path
            self.sync(child_path,
                g_drive_folder_id=child['id'])
