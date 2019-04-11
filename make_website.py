import argparse
import collections
import os
import subprocess

VERSION = '1.0'
SAL_TOPIC_BUCKET = 'sal-topic-registry'
BUCKET_WEBSITE = f'http://{SAL_TOPIC_BUCKET}.s3-website-us-west-2.amazonaws.com'
LSST_FONTS = 'http://fonts.googleapis.com/css?family=Raleway:subset=latin'
OUTPUT_LOCATION = 'website'
INDEX_FILE = 'index.html'
LS_EXCLUDES = [INDEX_FILE, 'css', 'images', '.gitignore']

def check_and_make_dirs(path):
    """Check for path existence and make all sub-directories if necessary

    Parameters
    ----------
    path : str
        The path to check and possibly create.
    """
    if not os.path.exists(path):
        os.makedirs(path)

def create_parser():
    """Create the script parser.

    Returns
    -------
    ArgParser
        The script argument parser.
    """
    description = ['This script generates the boiler plate index files for the SAL Topics']
    description.append('Registry website.')

    parser = argparse.ArgumentParser(usage='make_website.py [options]', description=' '.join(description),
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', dest='verbose', action='count', default=0,
                        help='Set the verbosity of the script. Add more flags for more info.')
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('-s', '--sync', dest='sync', action='store_true', default=False,
                        help='Synchronize the website directory with the AWS S3 bucket.')
    parser.add_argument('-b', '--base', dest='base', help='Set an alternative path for the website base.')

    return parser

def get_bucket_directories(verbose):
    """Parse the AWS S3 bucket for its directory structure.

    Parameters
    ----------
    verbose : int
        The current script level of verbosity.

    Returns
    -------
    dict
        Listing of all directories and topic HTML pages.
    """
    cmd = f'aws s3 ls s3://{SAL_TOPIC_BUCKET} --recursive'
    cmp_proc = subprocess.run(cmd.split(), capture_output=True)
    results = cmp_proc.stdout.split(b'\n')
    artifacts = collections.defaultdict(dict)
    for result in results:
        values = str(result).split()[-1].strip('\'')
        exclude_match = False
        for exclude in LS_EXCLUDES:
            if exclude in values:
                exclude_match = True
        if exclude_match or values == 'b':
            continue
        items = values.split(os.sep)
        if verbose > 3:
            print(items)
        if items[0] not in artifacts:
            artifacts[items[0]] = collections.defaultdict(list)
        artifacts[items[0]][items[1]].append(items[2])
        if verbose > 2:
            print(artifacts)
    if verbose > 1:
        print(artifacts)
    return artifacts

def get_local_directory():
    """Interpret the local path from the script.

    Returns
    -------
    str
        The absolute path of the script.
    """
    return os.path.dirname(os.path.abspath(__file__))

def make_html(path, key, items, opts):
    """Create the new HTML substructure.

    Parameters
    ----------
    path : str
        The top-level website path.
    key : str
        The topic version key.
    items : dict
        The CSC HTML substructure.
    opts : Namespace
        The argument parser contents.
    """
    save_path = os.path.join(path, key)
    check_and_make_dirs(save_path)
    write_html_index_file(save_path, {'title': f'SAL Topics for {key.capitalize()}'}, items.keys(), opts)
    for kitem, vitem in items.items():
        save_sub_path = os.path.join(save_path, kitem)
        check_and_make_dirs(save_sub_path)
        content = {'title': f'{kitem}', 'heading': f'{kitem}', 'link': True}
        write_html_index_file(save_sub_path, content, vitem, opts)

def write_html_index_file(path, content, links, opts):
    """Write the boiler plate HTML index files.

    The content dictionary must contain at least a title key with a
    corresponding string value. It may contain an optional key of heading and a
    corresponding string value to fill into the <h2> tag. It may contain an
    optional key of link and the value is ignored. If link is present, the
    link text is split at the '_' in the filename and only the last part is
    kept.

    Parameters
    ----------
    path : str
        The current website directory to contruct.
    content : dict
        Container to capture the fill-in content for the index page.
    links : list
        The set of directories or HTML pages to link against.
    opts : Namespace
        The argument parser contents.
    """
    template = []
    template.append('<!DOCTYPE html>\n')
    template.append('<html>\n')
    template.append('<head>\n')
    template.append(f'<title>{content["title"]}</title>\n')
    template.append(f'<link rel="stylesheet" type="text/css" href="{LSST_FONTS}" />')
    css_file = f'{opts.base}/css/default.css'
    template.append(f'<link rel="stylesheet" type="text/css" href="{css_file}" media="screen" />')
    template.append('</head>')
    template.append('<body>\n')
    if 'heading' in content:
        template.append(f'<h2>{content["heading"]}</h2>\n')
    for link in links:
        text = link.split('.')[0]
        if 'link' in content:
            text = text.split('_')[-1]
        template.append(f'<a href={link}>{text}</a><br />\n')
    template.append('</body>\n')
    template.append('</html>\n')

    with open(os.path.join(path, INDEX_FILE), 'w') as ofile:
        ofile.writelines(template)

def main(opts):
    """The top-level script function.

    Parameters
    ----------
    opts : Namespace
        The argument parser contents.
    """
    if opts.base is None:
        opts.base = BUCKET_WEBSITE
    artifacts = get_bucket_directories(opts.verbose)
    out_path = get_local_directory()
    web_dir = os.path.join(out_path, OUTPUT_LOCATION)
    write_html_index_file(web_dir, {'title': 'SAL Topics Frontpage',
                                    'heading': 'Version of SAL Topics'},
                          artifacts.keys(), opts)
    for dirkey in artifacts:
        make_html(web_dir, dirkey, artifacts[dirkey], opts)
    if opts.sync:
        cmd = f'aws s3 sync {web_dir}/ s3://{SAL_TOPIC_BUCKET} --acl public-read'
        cmp_proc = subprocess.run(cmd.split(), capture_output=True)
        results = cmp_proc.stdout.split(b'\n')
        if opts.verbose > 0:
            for result in results:
                print(result.decode('utf-8'))

if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    main(args)
