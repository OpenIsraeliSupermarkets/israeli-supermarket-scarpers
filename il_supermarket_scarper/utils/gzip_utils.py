import gzip
import shutil
import os,io
import zipfile

class Gzip:

    @staticmethod
    def extract_xml_file_from_gz_file(file_save_path):        
        try:
            with gzip.open(file_save_path, 'rb') as infile:
                with open(os.path.splitext(file_save_path)[0] + '.xml', 'wb') as outfile:
                    shutil.copyfileobj(infile, outfile)
        except gzip.BadGzipFile:

            try:
                with open(file_save_path, 'rb') as response_content:
                    with zipfile.ZipFile(io.BytesIO(response_content.read())) as the_zip:
                        zip_info = the_zip.infolist()[0]
                        with the_zip.open(zip_info) as the_file:
                            with open(os.path.splitext(file_save_path)[0] + '.xml', 'wb') as f_out:
                                f_out.write(the_file.read())
                
            except Exception as e:
                Gzip.report_failed_zip(e,file_save_path)
        
        except Exception as e:
            Gzip.report_failed_zip(e,file_save_path)
    
    def report_failed_zip(e,file_save_path):
        file_contant = ""
        with open(file_save_path,'r') as file:
            file_contant = file.readlines()
        file_size  = os.path.getsize(file_save_path)
        os.remove(file_save_path)
        raise ValueError('Error decoding file:' + file_save_path + "with error:" + str(e) + " file size "+str(file_size) + ",file_contant "+str(file_contant))