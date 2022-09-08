from il_supermarket_scarper.engines import Cerberus


class RamiLevy(Cerberus):

    def __init__(self,folder_name=None):
        super().__init__("Rami Levy", chain_id="7290058140886", folder_name=folder_name, ftp_username="RamiLevi")
    