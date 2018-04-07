import os
import ast
from itertools import filterfalse

import git

from fiasko_bro.config import VALIDATOR_SETTINGS
from .url_helpers import get_filename_from_path


class ParsedPyFile:

    def __init__(self, path, content):
        self.path = path
        self.content = content
        self.name = get_filename_from_path(path)
        self.ast_tree = self._generate_ast_tree(content)

    @staticmethod
    def _generate_ast_tree(content):
        try:
            tree = ast.parse(content)
        except SyntaxError:
            tree = None
        else:
            ParsedPyFile._set_parents(tree)
        return tree

    @staticmethod
    def _set_parents(tree):
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

    def is_in_whitelist(self, whitelist):
        for whitelisted_part in whitelist:
            if whitelisted_part in self.path:
                return True
        return False

    @property
    def is_syntax_correct(self):
        return self.ast_tree is not None

    def __str__(self):
        return 'ParsedPyFile object for the file {}'.format(self.name)

    def __repr__(self):
        return 'ParsedPyFile object for the file {}'.format(self.name)


class LocalRepositoryInfo:
    def __init__(self, repository_path):
        self.path = repository_path
        self._repo = git.Repo(self.path)
        self._parsed_py_files = self._get_parsed_py_files()

    def count_commits(self):
        return len(list(self._repo.iter_commits()))

    def does_file_exist(self, filename):
        return os.path.isfile(os.path.join(self.path, filename))

    def get_source_file_contents(self, extension_list):
        file_paths = []
        file_contents = []
        for dirname, directories_list, filenames in os.walk(self.path, topdown=True):
            directories_list[:] = [
                d for d in directories_list
                if d not in VALIDATOR_SETTINGS['directories_to_skip']
            ]
            for filename in filenames:
                extension = os.path.splitext(filename)[1]
                if extension in extension_list:
                    file_paths.append(os.path.join(dirname, filename))
        for file_path in file_paths:
            with open(file_path, 'r', encoding='utf-8') as file_handler:
                file_contents.append(file_handler.read())
        source_file_contents = list(zip(file_paths, file_contents))
        return source_file_contents

    def _get_parsed_py_files(self):
        py_files = self.get_source_file_contents(['.py']) or [(), ()]
        parsed_py_files = [ParsedPyFile(path, content) for path, content in py_files]
        return parsed_py_files

    def get_parsed_py_files(self, whitelist=None):
        parsed_py_files = self._parsed_py_files
        if whitelist:
            parsed_py_files = filterfalse(
                lambda parsed_file: parsed_file.is_in_whitelist(whitelist),
                parsed_py_files
            )
        return iter(parsed_py_files)

    def get_file(self, filename):
        for dirname, _, files in os.walk(self.path, topdown=True):
            for file in files:
                if file == filename:
                    with open(os.path.join(dirname, file), encoding='utf-8') as file_handler:
                        return file_handler.read()

    def does_directory_exist(self, dirname_to_find):
        for dirname, dirs, _ in os.walk(self.path, topdown=True):
            if dirname == dirname_to_find or dirname_to_find in dirs:
                return True
        return False

    def iter_commits(self, *args, **kwargs):
        return self._repo.iter_commits(*args, **kwargs)
