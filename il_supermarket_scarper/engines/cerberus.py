import ntpath
import os
from ftplib import FTP_TLS


from il_supermarket_scarper.utils import (extract_xml_file_from_gz_file,Logger,FileTypesFilters,
                                            download_connection_retry,
                                            execute_in_event_loop)
from .engine import Engine
class Cerberus(Engine):
    """ scraper for all Cerberus base site. (seems like can't support historical data) """
    target_file_extensions = ['xml','gz']

    def __init__(self, chain,chain_id, folder_name=None,
                    ftp_host='url.retail.publishedprices.co.il',ftp_path='/',
                    ftp_username= '',ftp_password= ''):
        super().__init__(chain, chain_id, folder_name)
        self.ftp_host = ftp_host
        self.ftp_path = ftp_path
        self.ftp_username = ftp_username
        self.ftp_password = ftp_password
        self.ftp_session = False

    def scrape(self,limit=None,files_types=None):
        super(Cerberus, self).scrape(limit=limit,files_types=files_types)
        files = self.collect_files_details_from_site(limit=limit,files_types=files_types,
                                                filter_null=True,filter_zero=True)
        self.on_collected_details(url_to_download=files)

        results = execute_in_event_loop(self.persist_from_ftp,files,max_workers=self.max_workers)
        self.on_download_completed(results=results)
        self.on_scrape_completed(self.get_storage_path())

    # @abstractmethod
    # def get_data_from_page(self,_):
    #     """ given a page """
    #     assert False, "shouldn't be in use."

    def collect_files_details_from_site(self,limit=None,files_types=None,
                                       filter_null=False,filter_zero=False):
        """ collect all files to download from the site """
        Logger.info(f"Open connection to FTP server with {self.ftp_host} "
                        ", username: {self.ftp_username} , password: {self.ftp_password}")
        self.ftp_session = FTP_TLS(self.ftp_host, self.ftp_username, self.ftp_password,timeout=60*5)
        self.ftp_session.set_pasv(True)
        self.ftp_session.cwd(self.ftp_path)
        files = self.ftp_session.nlst()
        self.ftp_session.quit()
        Logger.info(f"Found {len(files)} files")


        if filter_zero:
            files = list(filter(lambda x: "0000000000000" not in x,files)) # filter out files
            Logger.info(f"After filtering with '0000000000000': Found {len(files)} files")

        if filter_null:
            files = list(filter(lambda x: "NULL" not in x,files)) # filter out files
            Logger.info(f"After filtering with 'NULL': Found {len(files)} files")

        files = list(filter(lambda x:x.split(".")[-1] in self.target_file_extensions,files))
        Logger.info(f"After filtering by {self.target_file_extensions}: Found {len(files)} files")

        # apply noraml filter       
        files = self._apply_limit(files,limit=limit,files_types=files_types)
        Logger.info(f"After applying limit: Found {len(files)} files")

        return files

    @download_connection_retry()
    def fetch_temporary_gz_file_from_ftp(self, temporary_gz_file_path):
        """ download a file from a cerberus base site. """
        with open(temporary_gz_file_path, 'wb') as file_ftp:
            file_name = ntpath.basename(temporary_gz_file_path)
            ftp = FTP_TLS(self.ftp_host, self.ftp_username, self.ftp_password)
            ftp.cwd(self.ftp_path)
            ftp.retrbinary('RETR ' + file_name, file_ftp.write)
            ftp.quit()

    def persist_from_ftp(self, file_name):
        """ download file to hard drive and extract it."""
        downloaded = False
        extract_succefully = False
        additionl_info = {}
        try:
            ext = os.path.splitext(file_name)[1]
            if ext not in ['.gz','.xml']:
                raise ValueError(f"File {file_name} extension is not .gz or .xml")

            Logger.info(f"Start persisting file {file_name}")
            temporary_gz_file_path = os.path.join(self.storage_path, file_name)

            self.fetch_temporary_gz_file_from_ftp(temporary_gz_file_path)
            downloaded = True

            if ext == '.gz':
                extract_xml_file_from_gz_file(temporary_gz_file_path)

            Logger.info(f"Done persisting file {file_name}")
            extract_succefully = True
        except Exception as exception:
            Logger.error(f"Error downloading {file_name},extract_succefully={extract_succefully}"
                                    f",downloaded={downloaded}")
            Logger.error(exception)
            additionl_info = {"error":str(exception)}

        finally:
            if ext == '.gz' and os.path.exists(temporary_gz_file_path):
                os.remove(temporary_gz_file_path)

        return  {
                "file_name":file_name,
                "downloaded":downloaded,
                "extract_succefully":extract_succefully,
                **additionl_info
            }


