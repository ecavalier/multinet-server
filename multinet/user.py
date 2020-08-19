"""User data and functions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4
from copy import copy
from dacite import from_dict
from flask import session as flask_session

from multinet.db import user_collection

from typing import Optional, Dict

MULTINET_COOKIE = "multinet-token"


@dataclass
class MultinetInfo:
    """Multinet specific user metadata."""

    session: Optional[str] = None


@dataclass
class UserInfo:
    """Base info for a user."""

    family_name: str
    given_name: str
    name: str
    sub: str
    email: str
    picture: Optional[str] = None


def current_user() -> Optional[User]:
    """Return the logged in user (if any) from the current session."""
    cookie = flask_session.get(MULTINET_COOKIE)
    if cookie is None:
        return None

    return User.from_session(cookie)


def generate_user_session() -> str:
    """Generate a session."""
    return uuid4().hex


class User:
    """The class representing a user in multinet."""

    def __init__(
        self,
        family_name: str,
        given_name: str,
        name: str,
        sub: str,
        email: str,
        picture: Optional[str] = None,
        **kwargs
    ):
        """Construct user object."""
        self.family_name = family_name
        self.given_name = given_name
        self.name = name
        self.sub = sub
        self.email = email
        self.picture = picture

        # Keeps track of multinet metadata
        self.multinet: Optional[MultinetInfo] = None

    @staticmethod
    def exists(sub: str) -> bool:
        """Search the user collection for a user that has the matching `sub` value."""
        coll = user_collection()
        return not coll.find({"sub": sub}, limit=1).empty()

    @staticmethod
    def register(*args, **kwargs) -> User:
        """Register and return a user with the passed info."""
        user = User(*args, **kwargs)

        user.multinet = MultinetInfo(session=generate_user_session())
        user.save()

        return user

    @staticmethod
    def from_id(sub: str) -> Optional[User]:
        """Return a user from the passed `sub` value, if they exist."""
        coll = user_collection()

        try:
            res = next(coll.find({"sub": sub}, limit=1))
        except StopIteration:
            return None

        return User.from_dict(res)

    @staticmethod
    def from_session(session_id: str) -> Optional[User]:
        """Return a User from the session, if it exists."""
        coll = user_collection()

        try:
            return User.from_dict(
                next(coll.find({"multinet.session": session_id}, limit=1))
            )
        except StopIteration:
            return None

    @staticmethod
    def from_dict(d: Dict) -> User:
        """Return a user object from a dict."""
        keys = UserInfo.__annotations__.keys()
        filtered = {k: v for k, v in d.items() if k in keys}

        user = User(**filtered)
        user.multinet = from_dict(MultinetInfo, d["multinet"])

        return user

    def save(self):
        """Save this user into the user collection."""
        coll = user_collection()
        user_as_dict = self.asdict()
        done = False

        try:
            doc = next(coll.find({"sub": self.sub}, limit=1))
            dict_to_save = {**doc, **user_as_dict}
        except StopIteration:
            coll.insert(user_as_dict)
            done = True

        if not done:
            coll.update(dict_to_save)

    def get_session(self) -> str:
        """Return the login session of a user, creating it if it doesn't exist."""
        if self.multinet is None:
            self.multinet = MultinetInfo(session=generate_user_session())

        if self.multinet.session is None:
            self.multinet.session = generate_user_session()

        return self.multinet.session

    def set_session(self, session: str):
        """Set the login session of a user."""
        if self.multinet is None:
            self.multinet = MultinetInfo(session=session)
        else:
            self.multinet.session = session

        self.save()

    def delete_session(self):
        """Delete the login session of a user."""
        if self.multinet is not None:
            self.multinet.session = None
            self.save()

    def asjson(self) -> str:
        """Return this user as JSON."""
        return json.dumps(self.asdict())

    def asdict(self) -> Dict:
        """Return this user as a dict."""
        full_dict = copy(self.__dict__)
        full_dict["multinet"] = copy(self.multinet.__dict__)

        return full_dict
