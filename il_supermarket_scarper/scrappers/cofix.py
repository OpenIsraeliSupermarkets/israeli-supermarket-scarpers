from il_supermarket_scarper.engines import Cerberus
class Cofix(Cerberus):
    """ scraper for confix """
    def __init__(self,folder_name=None):
        super().__init__("cofix", chain_id="7291056200008", 
                    folder_name=folder_name, ftp_username="SuperCofixApp")
