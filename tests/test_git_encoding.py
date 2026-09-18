import subprocess


def test_git_commit_subjects_are_not_mojibake():
    """提交标题应保持可读文本，避免远程仓库目录列表出现乱码。"""
    output = subprocess.check_output(
        ["git", "log", "--all", "--format=%s"],
        text=True,
        encoding="utf-8",
    )
    mojibake_markers = ("�", "Ð", "Ã", "Â", "Í", "Î", "Ú")
    subjects = output.splitlines()
    assert subjects
    assert not any(
        marker in subject for subject in subjects for marker in mojibake_markers
    )
