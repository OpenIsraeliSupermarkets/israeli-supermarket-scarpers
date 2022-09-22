
import ntpath
import os
from ftplib import FTP_TLS


from il_supermarket_scarper.utils import Gzip,Logger,FileTypesFilters
from .engine import Engine
class Cerberus(Engine,FileTypesFilters):
    # seems like can't support historical data
    target_file_extensions = ['xml','gz']

    ftp = False

    def __init__(self, chain,chain_id, folder_name=None,ftp_host='url.retail.publishedprices.co.il',ftp_path='/',ftp_username= '',ftp_password= ''):
        super().__init__(chain, chain_id, folder_name)
        self.ftp_host = ftp_host
        self.ftp_path = ftp_path
        self.ftp_username = ftp_username
        self.ftp_password = ftp_password

    def scrape(self,limit=None,files_types=None):
        super(Cerberus, self).scrape(limit=limit,files_types=files_types)
        
        files = self.collect_details_from_site(limit=limit,files_types=files_types,filter_null=True,filter_zero=True)
        self.on_collected_details(url_to_download=files)

        results = self.execute_in_event_loop(self.persist_file,files)
        self.on_download_completed(results=results)
        self.on_scrape_completed(self.get_storage_path())

    def get_data_from_page(self,req_res):
        assert False, "shouldn't be in use."

    def collect_details_from_site(self,limit=None,files_types=None,filter_null=False,filter_zero=False):
        Logger.info("Open connection to FTP server with {} , username: {} , password: {}".format(self.ftp_host, self.ftp_username, self.ftp_password))
        self.ftp = FTP_TLS(self.ftp_host, self.ftp_username, self.ftp_password,timeout=60*5)
        self.ftp.set_pasv(True)
        self.ftp.cwd(self.ftp_path)
        files = self.ftp.nlst()
        self.ftp.quit()
        Logger.info("Found {} files".format(len(files)))
        

        if filter_zero:
            files = list(filter(lambda x: "0000000000000" not in x,files)) # filter out files 
            Logger.info("After filtering with '0000000000000': Found {} files".format(len(files)))

        if filter_null:
            files = list(filter(lambda x: "NULL" not in x,files)) # filter out files 
            Logger.info("After filtering with 'NULL': Found {} files".format(len(files)))

        files = list(filter(lambda x:x.split(".")[-1] in self.target_file_extensions,files))
        Logger.info("After filtering by {}: Found {} files".format(self.target_file_extensions,len(files)))
        
        files = self._apply_limit(files,limit=limit,files_types=files_types)
        Logger.info("After applying limit: Found {} files".format(len(files)))

        return files
     
    def persist_file(self, file_name):
        downloaded = False
        extract_succefully = False
        additionl_info = {}
        try:
            ext = os.path.splitext(file_name)[1]
            if ext not in ['.gz','.xml']:
                raise ValueError(f"File {file_name} extension is not .gz or .xml")
            
            Logger.info("Start persisting file {}".format(file_name))
            temporary_gz_file_path = os.path.join(self.storage_path, file_name)

            self.fetch_temporary_gz_file(temporary_gz_file_path)
            downloaded = True
            
            if ext == '.gz':
                Gzip.extract_xml_file_from_gz_file(temporary_gz_file_path)

            Logger.info("Done persisting file {}".format(file_name))
            extract_succefully = True
        except Exception as e:
            Logger.error(e)
            additionl_info = {"error":str(e)}
        
        finally:
            if ext == '.gz' and os.path.exists(temporary_gz_file_path):
                os.remove(temporary_gz_file_path)
        
        return  {
                "file_name":file_name,
                "downloaded":downloaded,
                "extract_succefully":extract_succefully,
                **additionl_info
            }

    def fetch_temporary_gz_file(self, temporary_gz_file_path):
        with open(temporary_gz_file_path, 'wb') as file_ftp:
            file_name = ntpath.basename(temporary_gz_file_path)
            ftp = FTP_TLS(self.ftp_host, self.ftp_username, self.ftp_password)
            ftp.cwd(self.ftp_path)
            ftp.retrbinary('RETR ' + file_name, file_ftp.write)
            ftp.quit()