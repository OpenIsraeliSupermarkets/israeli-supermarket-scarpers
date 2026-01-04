class FilterState:
    """Track the state of files as they pass through filters"""

    def __init__(self):
        self.total_input = 0
        self.after_already_downloaded = 0
        self.after_unique = 0
        self.after_store_id = 0
        self.after_file_types = 0
        self.after_date_filter = 0
        self.final_output = 0
        self.files_was_filtered_since_already_download = False
        self.unique_seen = set()
        self.file_pass_limit = 0
