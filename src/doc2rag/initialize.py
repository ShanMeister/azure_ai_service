from pathlib import Path

from .config_utils import PathConfig


class Initializer:

    def __init__(self):
        self.config = PathConfig()

        # Initialize base directory
        self.base_dir = self.config.base_dir

        # Initialize log, metadata directories
        self.log_dir = self.config.log_dir_path
        self.meta_data_dir = self.config.meta_data_dir_path
        self.indices_dir = self.config.indices_dir_path

    def create_dirs(self) -> None:
        # first layer
        # ensure user the base directory will be created
        if not self.base_dir.exists():
            if self._ask_user(f"Create base directory: {self.base_dir}"):
                self._create_dirs([self.base_dir])
            else:
                print("Exiting program...")
                exit(0)

        if not self.indices_dir.exists():
            if self._ask_user(f"Create indices directory: {self.indices_dir}"):
                self._create_dirs([self.indices_dir])
            else:
                print("Exiting program...")

        # second layer
        self._create_dirs([self.log_dir, self.meta_data_dir])

        # index-related directories
        for index in self.config.index_list:
            self._create_dirs(
                [
                    self.config.get_index_dir(index),
                    self.config.get_source_dir(index, "text"),
                    self.config.get_wait_dir(index, "text"),
                    self.config.get_done_dir(index, "text"),
                    self.config.get_fail_dir(index, "text"),
                    self.config.get_source_dir(index, "text_image"),
                    self.config.get_wait_dir(index, "text_image"),
                    self.config.get_done_dir(index, "text_image"),
                    self.config.get_fail_dir(index, "text_image"),
                ]
            )

    def _ask_user(self, msg: str) -> bool:
        return input(f"{msg} [y/n]: ").lower() == "y"

    def _create_dirs(self, dirs: list[Path]) -> None:
        for dir in dirs:
            if not dir.exists():
                dir.mkdir(parents=True, exist_ok=True)
                print(f"Created directory: {dir}")
            else:
                print(f"Directory already exists: {dir}")
