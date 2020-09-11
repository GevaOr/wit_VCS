import datetime
import distutils.dir_util
import os
import pathlib
import random
import shutil
import sys

from dateutil import tz

from graphviz import Digraph


user_input = sys.argv


class NoPathError(Exception):
    pass


def init():
    parent_dir = os.path.join(os.getcwd(), ".wit")
    paths_to_create = ["images", "staging_area"]
    for path in paths_to_create:
        os.makedirs(os.path.join(parent_dir, path), exist_ok=True)
    set_active_branch(parent_dir, "master")


def add(add_to_staging):
    try:
        parent_dir = find_wit_folder_location()
        path_to_add = os.path.abspath(add_to_staging).replace(
            str(f"{parent_dir}\\"), "")
    except NoPathError as err:
        raise err
    staging_area_dir = os.path.join(
        os.path.join(parent_dir, r".wit\staging_area"))
    if os.path.isdir(add_to_staging):
        internal_dir = os.path.join(staging_area_dir, path_to_add)
        os.makedirs(internal_dir, exist_ok=True)
        distutils.dir_util.copy_tree(os.path.join(
            parent_dir, path_to_add), internal_dir)
        return
    elif os.path.isfile(add_to_staging):
        if add_to_staging in os.listdir(parent_dir):
            shutil.copy(add_to_staging, staging_area_dir)
            return
        else:
            dest_dir = os.path.join(
                staging_area_dir, os.path.dirname(path_to_add))
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy(add_to_staging, dest_dir)
    else:
        print(add_to_staging)
        raise NoPathError("invalid path to add")


def find_wit_folder_location():
    path_tree_len = len(os.getcwd().split("\\"))
    current_path = pathlib.Path(os.getcwd())
    for _ in range(path_tree_len):
        wit_dir = os.path.join(current_path, ".wit")
        if os.path.isdir(wit_dir):
            return current_path
        current_path = current_path.parent
    raise NoPathError(".wit folder doesn't exist")


def commit(message="No message."):
    chars_to_use = "1234567890abcdef"
    file_name_len = 40
    try:
        wit_dir = os.path.join(find_wit_folder_location(), ".wit")
        images_dir = os.path.join(wit_dir, "images")
        staging_dir = os.path.join(wit_dir, "staging_area")
    except NoPathError as err:
        raise err
    folder_name = "".join(random.choice(chars_to_use)
                          for _ in range(file_name_len))
    try:
        head = get_data_from_references_file(wit_dir, "HEAD")
        master = get_data_from_references_file(wit_dir, "master")
    except FileNotFoundError:
        head, master = folder_name, folder_name
        overwrite_references_txt_file(folder_name, folder_name, wit_dir)
    commit_folder_dir = os.path.join(images_dir, folder_name)
    os.makedirs(commit_folder_dir)
    create_commit_txt_file(message, folder_name, images_dir, head)
    distutils.dir_util.copy_tree(staging_dir, commit_folder_dir)
    active_branch = get_active_branch(wit_dir)
    print(f"head: {head}")
    print(f"active branch: {active_branch}")
    if active_branch:
        branch_id = get_data_from_references_file(wit_dir, active_branch)
        print(f"branch id: {branch_id}")
        print(f"head: {head}")
        if (head == master) and (active_branch == "master"):
            overwrite_references_txt_file(folder_name, folder_name, wit_dir)
            return
        if head == branch_id:
            print("if head == branch_id:")
            update_branch_id(active_branch, folder_name, wit_dir)
            update_head(wit_dir, folder_name)
            return
    overwrite_references_txt_file(folder_name, master, wit_dir)
    return


def create_commit_txt_file(message, commit_id, images_path, parent):
    now = datetime.datetime.now(tz.tzlocal())
    formatted_now = now.strftime("%a %b %d %H:%M:%S %Y %z")
    with open(os.path.join(images_path, f"{commit_id}.txt"), "w") as f:
        f.write(f"""parent={parent}
date={formatted_now}
message={message}
        """)


def update_branch_id(branch_name, current_id, wit_path):
    ref_path = os.path.join(wit_path, "references.txt")
    try:
        ref_lines = open(ref_path, "r").readlines()
    except FileNotFoundError:
        raise
    for i, line in enumerate(ref_lines):
        if line.split("=")[0] == branch_name:
            ref_lines[i] = f"{branch_name}={current_id}"
            ref_write = open(ref_path, "w")
            ref_write.writelines(ref_lines)
            ref_write.close()
            return


def overwrite_references_txt_file(head, master, wit_path):
    ref_path = os.path.join(wit_path, "references.txt")
    try:
        ref_lines = open(ref_path, "r").readlines()
        print(f"at try\n{ref_lines}")
    except FileNotFoundError:
        ref_lines = ["", ""]
        print(f"at except\n{ref_lines}")
    ref_lines[0] = f"HEAD={head}\n"
    ref_lines[1] = f"master={master}\n"
    print(f"after overwrite\n{ref_lines}")
    ref_write = open(ref_path, "w")
    ref_write.writelines(ref_lines)
    ref_write.close()


def status(mode="print"):
    status_dict = {}
    try:
        parent_dir = pathlib.Path(find_wit_folder_location())
        wit_dir = os.path.join(parent_dir, ".wit")
        head = get_data_from_references_file(wit_dir, "HEAD")
    except NoPathError:
        raise
    status_dict["HEAD"] = head
    images_dir = os.path.join(wit_dir, "images")
    staging_dir = pathlib.Path(os.path.join(wit_dir, "staging_area"))
    head_dir = pathlib.Path(os.path.join(images_dir, head))
    parent_files = get_all_file_names(parent_dir)
    staging_files = get_all_file_names(staging_dir)
    head_files = get_all_file_names(head_dir)
    to_be_committed = staging_files - head_files
    status_dict["Changes to be committed"] = to_be_committed
    not_staged_for_commit = set()
    for file in staging_files:
        if is_not_similar_to_main(parent_dir, staging_dir, file):
            not_staged_for_commit.add(file)
    status_dict["Changes not staged for commit"] = not_staged_for_commit
    untracked = parent_files - staging_files
    status_dict["Untracked files"] = untracked
    if mode == "print":
        print_status_message(status_dict)
    elif mode == "return":
        return status_dict


def is_valid_commit_id(test_id):
    try:
        images_dir = os.path.join(find_wit_folder_location(), ".wit\\images")
    except NoPathError as err:
        raise err
    if os.path.exists(os.path.join(images_dir, test_id)):
        return True
    return False


def print_status_message(status_dict):
    status_message = ""
    for title, content in status_dict.items():
        if title == "HEAD":
            status_message += f"\n{title}: {content}\n\n"
        else:
            content_str = "\n".join(content)
            status_message += f"{title}:\n{content_str}\n\n"
    print(status_message)


def is_not_similar_to_main(main_dir, other_dir, file_path_in_dir):
    file_in_main = pathlib.Path(os.path.join(
        main_dir, file_path_in_dir))
    file_in_other = pathlib.Path(os.path.join(
        other_dir, file_path_in_dir))
    return file_in_main.read_bytes() != file_in_other.read_bytes()


def get_all_file_names(path):
    file_set = set()
    for current_dir in list(path.glob("**\\*")):
        if os.path.isfile(current_dir):
            inner_dir = str(current_dir).replace(f"{path}\\", "")
            if not str(inner_dir).startswith(".wit\\"):
                file_set.add(inner_dir)
    return file_set


def get_data_from_references_file(wit_path, search_word):
    ref_dict = {}
    try:
        with open(os.path.join(wit_path, "references.txt"), "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise
    else:
        for line in lines:
            sep_line = line.split("=")
            ref_dict[sep_line[0]] = sep_line[1]
    return ref_dict[search_word].strip()


def checkout(commit_id):
    try:
        main_dir = find_wit_folder_location()
        status_dict = status("return")
    except NoPathError as err:
        raise err
    wit_dir = os.path.join(main_dir, ".wit")
    staging_area_dir = os.path.join(wit_dir, "staging_area")
    if not is_valid_commit_id(commit_id):
        branch_name = commit_id
        try:
            commit_id = get_data_from_references_file(wit_dir, branch_name)
        except (NoPathError, KeyError):
            print("Invalid branch name or commit id")
            return
        else:
            set_active_branch(wit_dir, branch_name)
    else:
        set_active_branch(wit_dir, "")
    to_be_committed = status_dict["Changes to be committed"]
    not_staged_for_commit = status_dict["Changes not staged for commit"]
    if to_be_committed or not_staged_for_commit:
        print("""
You have files that should be committed or files that are not staged to commit.
Please check the status below for details:""")
        status()
        return
    commit_folder = os.path.join(wit_dir, f"images\\{commit_id}")
    distutils.dir_util.copy_tree(commit_folder, str(main_dir))
    update_head(wit_dir, commit_id)
    shutil.rmtree(staging_area_dir)
    distutils.dir_util.copy_tree(commit_folder, staging_area_dir)


def set_active_branch(wit_dir, branch_name):
    with open(os.path.join(wit_dir, "activated.txt"), "w") as act_f:
        act_f.write(branch_name)


def update_head(wit_dir, commit_id):
    current_master = get_data_from_references_file(wit_dir, "master")
    overwrite_references_txt_file(commit_id, current_master, wit_dir)


def graph():
    try:
        wit_dir = os.path.join(find_wit_folder_location(), ".wit")
        current_head = get_data_from_references_file(wit_dir, "HEAD")
    except (NoPathError, FileNotFoundError) as err:
        raise err
    images_path = pathlib.Path(os.path.join(wit_dir, "images"))
    g = Digraph('G', filename='.wit\\wit_graph', format='png')
    g.attr(rankdir='RL')
    g.edge_attr.update(arrowhead='vee', arrowsize='1.5')
    g.node("H", "", style="invis")
    g.edge("H", current_head[:6], label="HEAD")
    updated_graph = create_edges(images_path, g)
    updated_graph.view()


def create_edges(images_path, digraph):
    for file in list(images_path.glob("*.txt")):
        parents = get_parent(file).split(",")
        for parent in parents:
            if parent != file.stem:
                digraph.edge(parent[:6], file.stem[:6])
    return digraph


def get_parent(commit_file):
    with open(commit_file, "r") as f:
        parent = f.readline().split("=")[1].strip()
    return parent


def get_next_parent(images_dir, commit_id):
    current_id = commit_id
    while True:
        with open(f"{os.path.join(images_dir, current_id)}.txt", "r") as f:
            parent = f.readline().split("=")[1].strip().split(",")
        if current_id == parent:
            return
        if "," in parent:
            parents = parent.split(",")
            if (parents[0] != current_id) or (parents[1] != current_id):
                yield parent.split(",")
        yield parent
        current_id = parent


def branch(name):
    try:
        wit_dir = os.path.join(find_wit_folder_location(), ".wit")
        head = get_data_from_references_file(wit_dir, "HEAD")
    except NoPathError:
        raise
    with open(os.path.join(wit_dir, "references.txt"), "a") as ref:
        ref.write(f"{name}={head}\n")


def get_active_branch(wit_dir):
    with open(os.path.join(wit_dir, "activated.txt"), "r") as act_f:
        return act_f.read()


def merge(branch_name):
    try:
        wit_dir = os.path.join(find_wit_folder_location(), ".wit")
        head_id = get_data_from_references_file(wit_dir, "HEAD")
        branch_id = get_data_from_references_file(wit_dir, branch_name)
    except KeyError as err:
        raise err
    if head_id == branch_id:
        print(f"HEAD and {branch_name} are already merged.")
        return
    images_dir = os.path.join(wit_dir, "images")
    branch_dir = os.path.join(images_dir, branch_id)
    staging_dir = os.path.join(wit_dir, "staging_area")
    parent_commit_id = find_common_commit(images_dir, head_id, branch_id)
    parent_commit_dir = os.path.join(images_dir, parent_commit_id)
    changed_files = find_changed_files(parent_commit_dir, branch_dir)
    for file in changed_files:
        path_in_branch = os.path.join(branch_dir, file)
        path_in_staging = os.path.join(staging_dir, file)
        shutil.copyfile(path_in_branch, path_in_staging)
    commit(f"Merge branch: {branch_name}")
    new_commit = get_data_from_references_file(wit_dir, "HEAD")
    set_active_branch(wit_dir, new_commit)
    parents_str = f"{head_id},{branch_id}"
    update_parents(new_commit, parents_str, images_dir)


def update_parents(commit_id, parents_str, images_dir):
    commit_path = os.path.join(images_dir, f"{commit_id}.txt")
    commit_lines = open(commit_path, "r").readlines()
    commit_lines[0] = f"parent={parents_str}\n"
    commit_write = open(commit_path, "w")
    commit_write.writelines(commit_lines)
    commit_write.close()


def find_common_commit(images_dir, head_id, branch_id):
    for head_parent in get_next_parent(images_dir, head_id):
        for branch_parent in get_next_parent(images_dir, branch_id):
            if isinstance(head_parent, list):
                head_parent = check_multiple_parents(
                    head_parent, branch_parent)
            if isinstance(branch_parent, list):
                branch_parent = check_multiple_parents(
                    branch_parent, head_parent)
            if head_parent == branch_parent:
                return head_parent


def check_multiple_parents(parent_list, compare_to_this):
    for item in parent_list:
        if isinstance(compare_to_this, list):
            compare_to_this = check_multiple_parents(compare_to_this, item)
        if item == compare_to_this:
            return item
    return ""


def find_changed_files(parent_dir, branch_dir):
    branch_files = get_all_file_names(pathlib.Path(branch_dir))
    changed_files = set()
    for file in branch_files:
        try:
            if is_not_similar_to_main(parent_dir, branch_dir, file):
                changed_files.add(file)
        except FileNotFoundError:
            changed_files.add(file)
    return changed_files


if __name__ == '__main__':
    if len(user_input) > 1:
        if user_input[1] == "init":
            init()
        elif user_input[1] == "add":
            if len(user_input) < 3:
                raise NoPathError("no path was given")
            else:
                add(sys.argv[2])
        elif user_input[1] == "commit":
            if len(user_input) < 3:
                commit()
            else:
                commit(user_input[2])
        elif user_input[1] == "status":
            status()
        elif user_input[1] == "checkout":
            if len(user_input) < 3:
                raise NoPathError("no commit_id was given")
            else:
                checkout(user_input[2])
        elif user_input[1] == "graph":
            graph()
        elif user_input[1] == "branch":
            if len(user_input) < 3:
                print("Useage:\npython path\\to\\wit.py branch NAME")
            else:
                branch(user_input[2])
        elif user_input[1] == "merge":
            if len(user_input) < 3:
                print("Useage:\npython path\\to\\wit.py merge BRANCH_NAME")
            else:
                merge(user_input[2])
        else:
            print("""
Useage: python path\\to\\wit.py ACTION

Available actions:
    init
    add PATH\\TO\\ADD
    commit MESSAGE(optional)
    status
    checkout COMMIT_ID(or master)
    graph
    branch NAME
    merge BRANCH_NAME
            """)
