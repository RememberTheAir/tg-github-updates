import os
import logging
import re
import time
from datetime import datetime
from datetime import timedelta
from html import escape
from typing import List

from lxml import html

from bs4 import BeautifulSoup
import requests
from github import Github, Branch, Repository, Commit as GithubCommit
from github.GithubException import UnknownObjectException
from github import GitRelease
from telegram.error import BadRequest
from telegram.error import TelegramError
from telegram import Bot
from telegram import ParseMode
from telegram import MAX_MESSAGE_LENGTH

from config import config
from config import repos
from database import Commit
from database import Release
from database import DoesNotExist
from matrix import Matrix
from matrix import FakeMatrix
from sender import Sender
import utils as u

logger = logging.getLogger(__name__)

if config.github.access_token:
    logger.info('logging in to gitHub via access_token')
    g = Github(config.github.access_token)
else:
    logger.info('logging in to gitHub via user/password')
    g = Github(config.github.user, config.github.password)


if config.matrix.enabled:
    matrix_client = Matrix()
else:
    matrix_client = FakeMatrix()


NEW_RELEASE_STRING = """<a href="{release_url}">New {repo_name} release</a>: \
<code>{release_tag}</code> ({channel})
{release_body}

#{hashtag}"""

NEW_RELEASE_DOWNLOAD = """

<b>Download</b>:
{assets_download}"""

ASSET_STRING = '• <a href="{asset_download}">{asset_label}</a>'

CAPTION = """<b>{asset_label}</b>
<b>md5</b>: <code>{md5}</code>
<b>sha1</b>: <code>{sha1}</code>"""

NEW_COMMIT_STRING = """<a href="{branch_url}">{repo_name}</a> • <a href="{commit_url}">{commit_sha}</a> • <i>{n_files} files, +{commit_additions}/-{commit_deletions}</i>
{commit_message}"""

NEW_BETA_CAPTION = """🎉 <b>New Android Beta!</b>

<b>Version</b>: <code>{app_version}</code> ({build_number})"""

NEW_BETA_HASHES = """<b>md5</b>: <code>{md5}</code>
<b>sha1</b>: <code>{sha1}</code>"""


def append_hashtag(text, hashtag):
    if not hashtag:
        return text

    return '{}\n\n#{}'.format(text.strip(), hashtag)


@u.logerrors
def releases_job(bot, _):
    logger.info('running releases job at %s...', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if config.jobs.github.disable_releases:
        logger.info('releases job is disabled, exiting job')
        return

    sender = Sender(bot, matrix_client)

    for repo_desc, repo_data in repos.repos.items():
        if not repo_data.releases or not repo_data.chat_id:
            continue

        repo_name = repo_data.path
        logger.info('>>> loop: releases of %s', repo_desc)

        try:
            repo = g.get_repo(repo_name)
        except UnknownObjectException as e:
            logger.error('error while getting repo %s: %s', repo_name, str(e))
            continue

        try:
            releases = repo.get_releases()
        except Exception as e:
            error_string = str(e)
            logger.error('error while fetching repo %s releases: %s (continuing loop...)', repo_name, error_string)
            continue

        if len(list(releases)) == 0:
            logger.info('no releases for this repo, continuing to the next one...')
            continue

        if len(list(releases)) > 3:
            # we only need the first three
            releases = releases[:3]

        # the GitHub API has this weird bug that the most recent release is not always the first one
        # in the returned list, so we request the 3 most recent releases and find out which one to consider by ourself
        release: GitRelease = None
        for r in releases:
            if not release or r.created_at > release.created_at:
                # r.published_at can be used too
                release = r

        logger.info('most recent release among the last three: %s', release.tag_name)

        try:
            Release.get(Release.repository == repo_name, Release.release_id == release.id)
            logger.info('release %s (%s) is already saved in db, continuing to next repo...', release.id, release.tag_name)
            continue
        except DoesNotExist:
            logger.info('release %s (%s) is new, saving in db...', release.id, release.tag_name)
            db_release = Release.create(repository=repo_name, release_id=release.id)
            logger.info('...release record created, github release id: %d', db_release.release_id)

        assets_urls_list = []
        assets = release.get_assets()
        logger.info('%d assets found', len(list(assets)))
        for asset in assets:
            assets_urls_list.append(ASSET_STRING.format(
                asset_download=asset.browser_download_url,
                asset_label=asset.label
            ))

        assets_list_text = '\n'.join(assets_urls_list)

        text = NEW_RELEASE_STRING.format(
            release_url=release.html_url,
            release_tag=release.tag_name,
            release_body='\n' + release.body if release.body else '',
            repo_name=repo.full_name,
            channel='beta' if release.prerelease else 'stable',
            assets_download=assets_list_text,
            hashtag=repo_data.hashtag
        )

        new_release_message, _ = sender.send_message(repo_data, text)
        if new_release_message:
            # do not write the release id on the file so the job will retry to send that the next time

            db_release.post_id = new_release_message.message_id
            db_release.save()

    logger.info('job finished')


@u.logerrors
def commits_job(bot, _):
    logger.info('running commits job at %s...', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if config.jobs.github.disable_commits:
        logger.info('commits job is disabled, exiting job')
        return

    sender = Sender(bot, matrix_client)

    from_date = datetime.now() - timedelta(days=config.jobs.github.commits_days_backwards)

    for repo_desc, repo_data in repos.repos.items():
        if not repo_data.commits or not repo_data.chat_id:
            continue

        repo_name = repo_data.path
        logger.info('>>> loop: commits of %s', repo_desc)

        try:
            repo: Repository = g.get_repo(repo_name)
        except UnknownObjectException as e:
            logger.error('error while getting repo %s: %s', repo_name, str(e))
            continue

        branches: List[Branch] = list(repo.get_branches())
        branches_count = len(branches)
        if branches_count == 1:
            logger.info('repo has only one branch')
        else:
            logger.info('repo has %d branches: %s', branches_count, ', '.join([b.name for b in branches]))

        branch: Branch
        for branch in branches:
            if repo_data.branch and branch.name.lower() != repo_data.branch.lower():
                logger.info("branch %s is not the tracked one, continuing...", branch.name)
                continue

            if repo_data.get('ignored_branches', None) and branch.name in repo_data.ignored_branches:
                logger.info("branch %s is ignored, continuing...", branch.name)
                continue

            if branch.name.startswith("dependabot"):
                logger.info("ignoring branch %s: dependabot branch", branch.name)
                continue

            logger.info('getting commits of %s/%s', repo_name, branch.name)

            commits = repo.get_commits(since=from_date, sha=branch.commit.sha)
            logger.info('fetched %d total commits since %s (%d days ago)', len(list(commits)),
                        from_date.strftime("%Y-%m-%d %H:%M:%S"),
                        config.jobs.github.commits_days_backwards)

            combined_message = ''

            # reverse commits order
            commits: List[GithubCommit] = [commit for commit in commits]
            for commit in reversed(commits):
                try:
                    Commit.get(Commit.repository == repo_name, Commit.sha == commit.sha)
                    logger.info('commit %s is already saved in db, continuing...', commit.sha)
                    continue
                except DoesNotExist:
                    logger.info('commit %s is new, saving in db...', commit.sha)
                    Commit.create(repository=repo_name, sha=commit.sha)

                single_commit_text = NEW_COMMIT_STRING.format(
                    branch_url='{}/tree/{}'.format(repo.html_url, branch.name),
                    repo_name='{}/{}'.format(repo.full_name, branch.name),
                    commit_message=escape(commit.commit.message),
                    commit_url=commit.html_url,
                    commit_sha=commit.sha[:7],
                    # use only the first 7 characters
                    # https://stackoverflow.com/questions/18134627/how-much-of-a-git-sha-is-generally-considered-necessary-to-uniquely-identify-a
                    n_files=len(commit.files),
                    commit_additions=commit.stats.additions,
                    commit_deletions=commit.stats.deletions,
                )

                if (len(combined_message) + len(single_commit_text)) > MAX_MESSAGE_LENGTH:
                    logger.info('combined text reached max length: sending commit message...')
                    combined_message += '\n\n#{}'.format(repo_data.hashtag)
                    sender.send_message(repo_data, combined_message)
                    combined_message = ''

                combined_message = '{}\n\n{}'.format(combined_message, single_commit_text)

            logger.info('sending commit message after the loop (if not empty)...')
            if combined_message.strip():
                combined_message = append_hashtag(combined_message, repo_data.hashtag)
                sender.send_message(repo_data, combined_message)
            else:
                logger.info('...it\'s empty')

            time.sleep(3)

    logger.info('job finished')


@u.logerrors
def assets_job(bot, _):
    logger.info('running assets job at %s...', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if config.jobs.github.disable_assets:
        logger.info('assets job is disabled, exiting job')
        return

    # assets job: don't send messages to Matrix
    sender = Sender(bot, matrix_client=None)

    for repo_desc, repo_data in repos.repos.items():
        if not repo_data.releases or not repo_data.assets or not repo_data.chat_id:
            continue

        repo_name = repo_data.path
        logger.info('extracting latest release record for %s...', repo_desc)
        query = (
            Release.select()
            .where(Release.repository == repo_name, Release.added_on.is_null(False))
            .order_by(Release.added_on.desc())
            .limit(1)
        )

        if not query:
            logger.info('no release found for repo %s, continuing to next repo', repo_name)
            continue

        release = query[0]

        logger.info('repo %s latest release: %d, added on: %s', repo_name, release.release_id, str(release.added_on))
        if release.checked:
            logger.info('we already checked release %d of repo %s, continuing to next repo', release.release_id,
                        repo_name)
            continue

        # not all the repo have that attribute
        assets_timedelta = repo_data.get('assets_timedelta', config.jobs.github.assets_timedelta)

        # wait at least an hour before checking the assets
        tdelta = datetime.now() - release.added_on
        seconds_since_release = tdelta.total_seconds()
        if seconds_since_release < assets_timedelta:
            logger.info('time check: too soon to check assets, elapsed seconds: %d of %d', seconds_since_release, assets_timedelta)
            continue

        logger.info('time check: time to check assets, elapsed seconds: %d of %d', seconds_since_release, assets_timedelta)

        # mark the release as checked. We will check later whether to send download urls/files according to config
        logger.info('marking release as checked...')
        release.checked = True
        release.save()

        logger.info('getting github repo object...')
        try:
            repo = g.get_repo(repo_name)
        except UnknownObjectException as e:
            logger.error('error while getting repo %s: %s', repo_name, str(e))
            continue

        logger.info('getting github release object...')
        gh_release = repo.get_release(release.release_id)

        logger.info('getting release assets...')
        assets = gh_release.get_assets()
        logger.info('%d assets found', len(list(assets)))

        assets_urls_list = []
        for asset in assets:
            assets_urls_list.append(ASSET_STRING.format(
                asset_download=asset.browser_download_url,
                asset_label=asset.label or 'no label'
            ))

        if not assets_urls_list:
            logger.info('no asset to send, continuing to new repo...')
            continue

        assets_list_text = '<b>Assets for release</b> <code>{}</code> <b>of {}</b>:\n\n{}'.format(
            gh_release.tag_name,
            repo_data.path,
            '\n'.join(assets_urls_list)
        )
        assets_list_text = append_hashtag(assets_list_text, repo_data.hashtag)
        assets_message, _ = sender.send_message(repo_data, assets_list_text)

        if not repo_data.asset_files:
            logger.info('skipping assets sending as per configuration (release has been marked as checked)')
            continue

        for asset in assets:
            logger.info('downloading asset %s...', asset.name)
            try:
                file_path = u.download_to_file(asset.browser_download_url, asset.name)
            except Exception as e:
                logger.error('error while downloading asset %s: %s', asset.name, str(e), exc_info=True)
                continue

            try:
                md5, sha1 = u.get_md5_sha1(file_path)
            except Exception as e:
                logger.error('error while generating md5/sha1 for asset %s: %s', asset.name, str(e), exc_info=True)
                continue

            caption = CAPTION.format(md5=md5, sha1=sha1, asset_label=asset.label or 'non-labeled asset')
            logger.info('sending asset %s...', asset.name)
            try:
                with open(file_path, 'rb') as f:
                    assets_message.reply_document(f, caption=caption, parse_mode=ParseMode.HTML, timeout=300)
            except Exception as e:
                logger.error('error while sending the asset %s: %s', asset.name, str(e), exc_info=True)
                continue

            logger.info('removing file %s...', file_path)
            os.remove(file_path)

        release.sent = True
        release.save()

    logger.info('job finished')


@u.logerrors
def new_beta_job(bot, _):
    if not config.jobs.beta.enabled:
        logger.info('android beta job is disabled, exiting job')
        return

    logger.info('starting android beta job...')

    try:
        with open(config.jobs.beta.build_number_file, 'r') as f:
            latest_build_number = f.read().strip()
    except FileNotFoundError:
        latest_build_number = '-1'

    latest_build_number = int(latest_build_number)

    logger.info('last posted build: %d', latest_build_number)

    logger.info('executing request...')
    page_content = requests.get(config.jobs.beta.url)
    tree = html.fromstring(page_content.content)

    version_string = tree.xpath('/html/body/div[1]/div[2]/div/div[1]/div/div[3]/div[6]/h3')[0].text
    logger.info('scraped site version: %s', version_string)

    version_match = re.search(r'Version\s([0-9 .]+)\s\(([0-9]+)\)$', version_string, re.I)
    app_version, build_number = version_match.group(1), version_match.group(2)
    logger.info('scraped app version: %s; scraped build number: %s', app_version, build_number)

    build_number = int(build_number)

    if build_number == latest_build_number:
        logger.info('build_number == latest_build_number (%d == %d)', build_number, latest_build_number)
        return
    else:
        logger.info('scraped build number is different from the last posted one')

    apk_name = 'beta_{}_{}.apk'.format(app_version, build_number)
    logger.info('apk_name: %s', apk_name)

    soup = BeautifulSoup(page_content.text, 'html.parser')
    download_url = u.bs_find_first(soup, 'a')

    apk_path = u.download_to_file(download_url, apk_name)
    logger.info('apk_path: %s', apk_path)

    logger.info('getting md5/sha1...')
    md5, sha1 = None, None
    try:
        md5, sha1 = u.get_md5_sha1(apk_path)
    except Exception as e:
        error_string = str(e)
        logger.error('error while getting md5/sha1: %s', error_string, exc_info=True)
        bot.send_message(config.telegram.admins[0], 'Error while generating md5/sha1: ' + error_string)

    caption = NEW_BETA_CAPTION.format(
        app_version=app_version,
        build_number=build_number
    )

    logger.info('sending apk file')
    try:
        with open(apk_path, 'rb') as f:
            logger.info('reading and sending the APK...')
            sent_document = bot.send_document(config.jobs.beta.channel_id, f, caption=caption, parse_mode=ParseMode.HTML, timeout=300)
        logger.info('apk sent, removing file...')
        os.remove(apk_path)

        logger.info('saving last posted build number...')
        with open(config.jobs.beta.build_number_file, 'w+') as f:
            f.write(str(build_number))
    except Exception as e:
        error_string = str(e)
        logger.error('error while sending the apk: %s', error_string, exc_info=True)
        bot.send_message(config.telegram.admins[0], 'Error while sending apk: ' + error_string)

        return

    if md5 or sha1:
        # send them in a separate message
        text = NEW_BETA_HASHES.format(md5=md5 or 'error', sha1=sha1 or 'error')
        bot.send_message(config.jobs.beta.channel_id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    if config.jobs.beta.notify_channel_id:
        # notify in the main channel that a new beta has been released
        bot.send_message(
            config.jobs.beta.notify_channel_id,
            'New Android Beta released: https://t.me/{}/{}'.format(sent_document.chat.username, sent_document.message_id),
            disable_web_page_preview=True
        )

    logger.info('job finished')


JOBS_CALLBACKS = (
    releases_job,
    commits_job,
    assets_job,
    new_beta_job
)


def main():
    bot = Bot(token=config.telegram.token)

    for callback in JOBS_CALLBACKS:
        callback(bot, ())  # errors are catched by the decorator


if __name__ == "__main__":
    from main import load_logging_config
    load_logging_config()

    main()

