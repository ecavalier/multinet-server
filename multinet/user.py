"""User data and functions."""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, asdict, field
from uuid import uuid4
from arango.collection import StandardCollection
from arango.cursor import Cursor
from dacite import from_dict
from flask import session as flask_session

from multinet.db import db, user_collection
from multinet.errors import InternalServerError

# from multinet.auth.types import GoogleUserInfo, FilteredUser

from typing import Optional, Dict, Iterable

MULTINET_COOKIE = "multinet-token"


@dataclass
class MultinetInfo:
    session: Optional[str] = None

    def __post_init__(self):
        if self.session is None:
            self.session = uuid4().hex


@dataclass
class UserInfo:
    family_name: str
    given_name: str
    name: str
    sub: str
    email: str
    picture: Optional[str] = None


class User:
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
        self.family_name = family_name
        self.given_name = given_name
        self.name = name
        self.sub = sub
        self.email = email
        self.picture = picture

        # Keeps track of arangodb metadata
        self.arango: Optional[Dict] = None

        # Keeps track of multinet metadata
        self.multinet: Optional[MultinetInfo] = field(init=False, default=None)

    @staticmethod
    def exists(sub: str) -> bool:
        """Search the user collection for a user that has the matching `sub` value"""
        return User.from_id(sub) is not None

    @staticmethod
    def register(*args, **kwargs) -> User:
        coll = user_collection()
        user = User(*args, **kwargs)

        user.multinet = MultinetInfo()
        user.arango = coll.insert(asdict(user))
        return user

    @staticmethod
    def from_id(sub: str) -> Optional[User]:
        coll = user_collection()

        try:
            return from_dict(User, next(coll.find({"sub": sub}, limit=1)))
        except StopIteration:
            return None

    @staticmethod
    def from_session(session_id: str) -> Optional[User]:
        coll = user_collection()

        try:
            return from_dict(
                User, next(coll.find({"multinet.session": session_id}, limit=1))
            )
        except StopIteration:
            return None

    @staticmethod
    def search(query: str) -> Iterable[User]:
        pass

    def save(self) -> User:
        """Save this user into the user collection."""
        # TODO: NOT DONE
        coll = user_collection()
        if not self.arango:
            doc = next(coll.find({"sub": self.sub}, limit=1))
            # self.arango = {doc: }

        # coll.update(self.)

    def document(self) -> Dict:
        """Return the underlying arangodb user document."""
        pass

    def get_session(self) -> str:
        pass

    def set_session(self):
        pass

    def delete_session(self):
        pass

    def serialize(self):
        pass

    def asjson(self):
        return json.dumps(self.asdict())

    def asdict(self):
        full_dict = asdict(self)
        full_dict.pop("arango")
        full_dict.pop("multinet")

        return full_dict


# def user_collection() -> StandardCollection:
#     """Return the collection that contains user documents."""
#     sysdb = db("_system")

#     if not sysdb.has_collection("users"):
#         sysdb.create_collection("users")

#     return sysdb.collection("users")


# def updated_user(user: User) -> User:
#     """Update a user using the provided user object."""
#     coll = user_collection()
#     inserted_info = coll.update(dataclasses.asdict(user))

#     return from_dict(User, next(coll.find({"_id": inserted_info["_id"]}, limit=1)))


# def register_user(userinfo: UserInfo) -> User:
#     """Register a user with the given user info."""
#     coll = user_collection()

#     document = dataclasses.asdict(userinfo)
#     document["multinet"] = dataclasses.asdict(MultinetInfo())

#     inserted_info: Dict = coll.insert(document)
#     return from_dict(User, next(coll.find(inserted_info, limit=1)))


# def set_user_cookie(user: User) -> User:
#     """Update the user cookie."""
#     new_user = copy_user(user)

#     new_cookie = uuid4().hex
#     new_user.multinet.session = new_cookie

#     return updated_user(new_user)


# def delete_user_cookie(user: User) -> User:
#     """Delete the user cookie."""
#     user_copy = copy_user(user)

#     # Remove the session object from the user record, then persist that to the
#     # database.
#     user_copy.multinet.session = None
#     return updated_user(user_copy)


# def user_from_cookie(cookie: str) -> Optional[User]:
#     """Use provided cookie to load a user, return None if they dont exist."""
#     coll = user_collection()

#     try:
#         return from_dict(User, next(coll.find({"multinet.session": cookie}, limit=1)))
#     except StopIteration:
#         return None


def current_user() -> Optional[User]:
    """Return the logged in user (if any) from the current session."""
    cookie = flask_session.get(MULTINET_COOKIE)
    if cookie is None:
        return None

    # return user_from_cookie(cookie)
    return User.from_session(cookie)


# def get_user_cookie(user: User) -> str:
#     """Return the cookie from the user object, or create it if it doesn't exist."""

#     if user.multinet.session is None:
#         user = set_user_cookie(user)

#     if not isinstance(user.multinet.session, str):
#         raise InternalServerError("User cookie not set.")

#     return user.multinet.session


# def filter_user_info(info: GoogleUserInfo) -> UserInfo:
#     """Return a subset of the User Object."""
#     fields = {field.name for field in dataclasses.fields(UserInfo)}
#     info_dict = dataclasses.asdict(info)

#     return from_dict(UserInfo, {k: v for k, v in info_dict.items() if k in fields})


# def filtered_user(user: User) -> FilteredUser:
#     """Remove ArangoDB metadata from a document."""
#     doc = dataclasses.asdict(user)

#     fields = {field.name for field in dataclasses.fields(FilteredUser)}
#     filtered = {k: v for k, v in doc.items() if k in fields}

#     return from_dict(FilteredUser, filtered)


# def copy_user(user: User) -> User:
#     """Create and return a new instance of User."""
#     return from_dict(User, dataclasses.asdict(user))


# def search_user(query: str) -> Cursor:
#     """Search for users given a partial string."""

#     coll = user_collection()
#     aql = read_only_db("_system").aql

#     bind_vars = {"@users": coll.name, "query": query}
#     query = """
#         FOR doc in @@users
#           FILTER CONTAINS(LOWER(doc.name), LOWER(@query))
#             OR CONTAINS(LOWER(doc.email), LOWER(@query))

#           LIMIT 50
#           RETURN doc
#     """

#     return _run_aql_query(aql, query, bind_vars)
