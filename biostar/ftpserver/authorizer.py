import logging
import os
import warnings



from django.contrib.auth.models import AnonymousUser
from biostar.accounts import auth as accounts_auth
from biostar.accounts.models import User

logger = logging.getLogger("engine")
logger.setLevel(logging.INFO)


class AuthenticationFailed(Exception):
    """Exception raised when authentication fails for any reason."""



class BiostarAuthorizer(object):

    """Copied from pyftpdlib, need to make out own user_table."""

    read_perms = "elr"
    write_perms = "adfmwMT"

    def __init__(self):
        self.user_table = {}

    def add_user(self, username, user=AnonymousUser, perm='elrwm',
                 msg_login="Login successful.", msg_quit="Goodbye."):

        data = {'user': user,
                'perm': perm,
                'operms': {},
                'msg_login': str(msg_login),
                'msg_quit': str(msg_quit),
                'home': "/"
                }

        self.user_table[username] = data


    def validate_authentication(self, username, password, handler):
        """
        Validate user with biostar.accounts and then add to user_table.
        The stored password in the user_table is a hashed-string
        """

        message, valid_django_user = accounts_auth.check_user(email=username, password=password)

        if valid_django_user:

            user = User.objects.filter(email__iexact=username).order_by('-id').first()
            # Stores the hash string
            #pwd = user.password

            if self.has_user(username=username):
                # Check if the user is added to user table with the correct password.
                return

            # Add to user_table since user is a valid biostar.account instance.
            self.add_user(username=username, user=user)
            return

        raise AuthenticationFailed(f"{message}. Resolve issue through website.")


    def remove_user(self, username):
        """Remove a user from the virtual users table."""
        del self.user_table[username]


    def override_perm(self, username, directory, perm, recursive=False):
        """Override permissions for a given directory."""

        logger.info(f"username={username}")
        self._check_permissions(username, perm)

        #if not os.path.isdir(directory):
        #    raise ValueError('no such directory: %r' % directory)
        directory = os.path.normcase(os.path.realpath(directory))
        home = os.path.normcase(self.get_home_dir(username))
        if directory == home:
            raise ValueError("can't override home directory permissions")
        if not self._issubpath(directory, home):
            raise ValueError("path escapes user home directory")

        self.user_table[username]['operms'][directory] = perm, recursive

    def get_home_dir(self, username):

        logger.info(f"{username}")
        return self.user_table[username]['home']


    def impersonate_user(self, username, password):
        """Impersonate another user (noop).
        It is always called before accessing the filesystem.
        By default it does nothing.  The subclass overriding this
        method is expected to provide a mechanism to change the
        current user.
        """

    def terminate_impersonation(self, username):
        """Terminate impersonation (noop).
        It is always called after having accessed the filesystem.
        By default it does nothing.  The subclass overriding this
        method is expected to provide a mechanism to switch back
        to the original user.
        """

    def has_user(self, username):
        """Whether the username exists in the virtual users table."""
        return username in self.user_table

    def has_perm(self, username, perm, path=None):
        """Whether the user has permission over path (an absolute
        pathname of a file or a directory).

        Expected perm argument is one of the following letters:
        "elradfmwMT".
        """
        if path is None:
            return perm in self.user_table[username]['perm']

        path = os.path.normcase(path)
        for dir in self.user_table[username]['operms'].keys():
            operm, recursive = self.user_table[username]['operms'][dir]
            if self._issubpath(path, dir):
                if recursive:
                    return perm in operm
                if (path == dir or os.path.dirname(path) == dir and not
                os.path.isdir(path)):
                    return perm in operm

        return perm in self.user_table[username]['perm']


    def get_perms(self, username):
        """Return current user permissions."""
        return self.user_table[username]['perm']

    def get_msg_login(self, username):
        """Return the user's login message."""
        return self.user_table[username]['msg_login']

    def get_msg_quit(self, username):
        """Return the user's quitting message."""
        try:
            return self.user_table[username]['msg_quit']
        except KeyError:
            return "Goodbye."


    def _check_permissions(self, username, perm):
        warned = 0
        for p in perm:
            if p not in self.read_perms + self.write_perms:
                raise ValueError('no such permission %r' % p)
            if (username == 'anonymous' and
                    p in self.write_perms and not
                    warned):
                warnings.warn("write permissions assigned to anonymous user.",
                              RuntimeWarning)
                warned = 1

    def _issubpath(self, a, b):
        """Return True if a is a sub-path of b or if the paths are equal."""
        p1 = a.rstrip(os.sep).split(os.sep)
        p2 = b.rstrip(os.sep).split(os.sep)
        return p1[:len(p2)] == p2

