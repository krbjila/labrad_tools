"""
Server for communicating with MongoDB databases

..
    ### BEGIN NODE INFO
    [info]
    name = database
    version = 1.0
    description = 
    instancename = %LABRADNODE%_database

    [startup]
    cmdline = %PYTHON3% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue
from pymongo import MongoClient, errors
from bson.json_util import loads, dumps

class DatabaseServer(LabradServer):
    """
    Server for communicating with MongoDB databases.

    Currently includes methods for inserting, modifying, and deleting data, and the basic query method :meth:`find_one`. 

    Uses :py:mod:`bson.json_util` for serializing and deserializing `BSON <https://bsonspec.org/>`__ data.
    """
    name = '%LABRADNODE%_database'

    def expireContext(self, c):
        """
        expireContext(self, c)

        Called when the context expires, typically by the client disconnecting.

        Calls :meth:`close`.

        Args:
            c: LabRAD context
        """

        self.close(c)

    @staticmethod
    def InsertOneResultToDict(result):
        """
        InsertOneResultToDict(res)

        Converts a :py:class:`pymongo.results.InsertOneResult` to a dictionary.

        Args:
            res (:py:class:`pymongo.results.InsertOneResult`): The result to convert to a dictionary

        Returns:
            dict: A dictionary containing the result's fields
        """

        return_dict = {"acknowledged": result.acknowledged}
        if return_dict["acknowledged"]:
            return_dict["inserted_id"] = result.inserted_id
        return return_dict

    @staticmethod
    def InsertManyResultToDict(result):
        """
        InsertManyResultToDict(res)

        Converts a :py:class:`pymongo.results.InsertManyResult` to a dictionary.

        Args:
            res (:py:class:`pymongo.results.InsertManyResult`): The result to convert to a dictionary

        Returns:
            dict: A dictionary containing the result's fields
        """

        return_dict = {"acknowledged": result.acknowledged}
        if return_dict["acknowledged"]:
            return_dict["inserted_ids"] = result.inserted_ids
        return return_dict

    @staticmethod
    def UpdateResultToDict(result):
        """
        UpdateResultToDict(res)

        Converts a :py:class:`pymongo.results.UpdateResult` to a dictionary.

        Args:
            res (:py:class:`pymongo.results.UpdateResult`): The result to convert to a dictionary

        Returns:
            dict: A dictionary containing the result's fields
        """

        return_dict = {"acknowledged": result.acknowledged}
        if return_dict["acknowledged"]:
            return_dict["upserted_id"] = result.upserted_id
            return_dict["matched_count"] = result.matched_count
            return_dict["modified_count"] = result.modified_count
            return_dict["raw_result"] = result.raw_result
        return return_dict

    @staticmethod
    def DeleteResultToDict(result):
        """
        DeleteResultToDict(res)

        Converts a :py:class:`pymongo.results.DeleteResult` to a dictionary.

        Args:
            res (:py:class:`pymongo.results.DeleteResult`): The result to convert to a dictionary

        Returns:
            dict: A dictionary containing the result's fields
        """

        return_dict = {"acknowledged": result.acknowledged}
        if return_dict["acknowledged"]:
            return_dict["deleted_count"] = result.deleted_count
            return_dict["raw_result"] = result.raw_result
        return return_dict

    @inlineCallbacks
    @setting(9, address='s', port='i', user='s', password='s', database='s', collection='s', timeout='i', returns='s')
    def connect(self, c, address=None, port=None, user=None, password=None, database=None, collection=None, timeout=2000):
        """
        connect(self, c, address=None, port=None, user=None, password=None, database=None, collection=None)

        Connect to a MongoDB database. Connections are maintained per LabRAD context.

        Args:
            c: LabRAD context
            address (str, optional): The address to connect to. Defaults to ``None``, in which case the address is loaded from ``mongodb.json`` if the file exists.
            port (str, optional): The port to connect to. Defaults to ``None``, in which case the port is loaded from ``mongodb.json`` if the file exists. If the port is not specified in the file, the default port is ``27017``.
            user (str, optional): The user to connect as. Defaults to ``None``, in which case the user is loaded from ``mongodb.json`` if the file exists.
            password (str, optional): The user's password. Defaults to ``None``, in which case the password is loaded from ``mongodb.json`` if the file exists.
            database (str, optional): The database to select. Defaults to ``None``, in which case :meth:set_database must be run to set the client's context's database.
            collection (str, optional): The database's collection to select. Defaults to ``None``, in which case :meth:set_collection must be run to set the client's context's database's collection.
            timeout (int, optional): The timeout in ms for connecting to the database (``connectTimeoutMS`` in :py:class:`pymongo.mongo_client.MongoClient`). Defaults to 2000.

        Returns:
            str: A BSON-dumped string of the result of :py:meth:`pymongo.mongo_client.MongoClient.server_info` if the connection was successful and the string ``{}`` otherwise.
        """

        if hasattr(c, 'c') and c.c is not None:
            self.close(c)
        c.c = None
        c.database = None
        c.collection = None

        try:
            with open('mongodb.json', 'r') as f:
                config = loads(f.read())
        except Exception as e:
            print("Could not load MongoDB config: {}".format(e))
            config = {}

        if address is None:
            if "address" in config:
                address = config["address"]
            else:
                print("Could not connect to MongoDB database. No address specified.")
                returnValue("{}")
        if port is None:
            if "port" in config:
                port = config["port"]
            else:
                port = 27017
        if user is None:
            if "user" in config:
                user = config["user"]
            else:
                print("Could not connect to MongoDB database. No user specified.")
                returnValue("{}")
        if password is None:
            if "password" in config:
                password = config["password"]
            else:
                print("Could not connect to MongoDB database. No password specified.")
                returnValue("{}")

        url = "mongodb://{}:{}@{}:{}/?authSource=admin".format(user, password, address, port)
        c.c = yield MongoClient(url)
        try:
            server_info = yield c.c.server_info()
            server_info_str = dumps(server_info)
            
            if database is not None:
                yield self.set_database(c, database)
                if collection is not None:
                    yield self.set_collection(c, collection)

            returnValue(server_info_str)
        except Exception as e:
            c.c = None
            print("Could not connect to MongoDB database: {}".format(e))
            returnValue("{}")
        

    @setting(10)
    def close(self, c):
        """
        close(self, c)

        Close the client's context's connection to the database.

        Args:
            c: LabRAD context
        """

        if c.c is not None:
            try:
                c.c.close()
            except Exception as e:
                print("Could not close MongoDB connection: {}".format(e))
        c.c = None

    @inlineCallbacks
    @setting(11, database='s', returns='b')
    def set_database(self, c, database):
        """
        set_database(self, c, database)

        Sets the database associated with the client's context.

        Args:
            c: LabRAD context
            database (str): The name of the database to use

        Returns:
            bool: ``True`` if the database exists, ``False`` otherwise
        """
        
        try:
            yield c.c[database]
            c.database = database
            returnValue(True)
        except errors.InvalidName:
            c.database = database
            returnValue(False)
        except Exception as e:
            print("Could not set database: {}".format(e))
            returnValue(False)

    @setting(12, collection='s', returns='b')
    def set_collection(self, c, collection):
        """
        set_collection(self, c, collection)

        Sets the collection associated with the client's context. :meth:set_database must already have been called.

        Args:
            c: LabRAD context
            collection (str): The name of the collection to use

        Returns:
            bool: ``True`` if the collection exists in the current database, ``False`` otherwise
        """
        try:
            yield c.c[c.database][collection]
            c.collection = collection
            returnValue(True)
        except errors.InvalidName:
            c.collection = collection
            returnValue(False)
        except Exception as e:
            print("Could not set database {}'s collection to {}: {}".format(c.database, collection, e))
            returnValue(False)

    @inlineCallbacks
    @setting(13, document='s', returns='s')
    def insert_one(self, c, document):
        """
        insert_one(self, c, document)

        Insert a single document.
        
        See :py:meth:`pymongo.collection.Collection.insert_one`.

        Args:
            c: LabRAD context
            document (str): BSON-dumped string of the document

        Returns:
            str: A BSON-dumped string of the :py:class:`pymongo.results.InsertOneResult` if the operation was successful and the string ``{}`` otherwise.
        """
        document = loads(document)
        try:
            result = yield c.c[c.database][c.collection].insert_one(document)
            returnValue(dumps(DatabaseServer.InsertOneResultToDict(result)))
        except Exception as e:
            print("Could not insert document into collection {} of database {}: {}".format(c.collection, c.database, e))
            returnValue("{}")

    @setting(14, documents='*s', ordered='b', returns='s')
    def insert_many(self, c, documents, ordered=True):
        """
        insert_many(self, c, documents, ordered=True)

        Inserts a list of documents.
        
        See :py:meth:`pymongo.collection.Collection.insert_many`.

        Args:
            c: LabRAD context
            documents (list of str): list of BSON-dumped strings of the documents to insert
            ordered (bool, optional): If ``True`` (the default) documents will be inserted on the server serially, in the order provided. If an error occurs all remaining inserts are aborted. If ``False``, documents will be inserted on the server in arbitrary order, possibly in parallel, and all document inserts will be attempted.

        Returns:
            str: A BSON-dumped string of the :py:class:`pymongo.results.InsertManyResult` if the operation was successful and the string ``{}`` otherwise.
        """
        documents = [loads(document) for document in documents]
        try:
            result = yield c.c[c.database][c.collection].insert_many(documents, ordered=ordered)
            returnValue(dumps(DatabaseServer.InsertManyResultToDict(result)))
        except Exception as e:
            print("Could not insert documents into collection {} of database {}: {}".format(c.collection, c.database, e))
            returnValue("{}")

    @setting(15, db_filter='s', replacement='s', upsert='b', returns='s')
    def replace_one(self, c, db_filter, replacement, upsert=False):
        """
        replace_one(self, c, db_filter, replacement, upsert=False)

        Replace a single document matching ``db_filter`` with ``replacement``.
        
        See :py:meth:`pymongo.collection.Collection.replace_one` for information on how ``db_filter`` (called ``filter`` in the documentation) and ``replacement`` work.

        Args:
            c: LabRAD context
            db_filter (str): BSON-dumped string of the filter
            replacement (str): BSON-dumped string of update
            upsert (bool, optional): Whether to create a document if none exists. Defaults to ``False``.

        Returns:
            str: A BSON-dumped string of the :py:class:`pymongo.results.UpdateResult`
        """
        replacement = loads(replacement)
        db_filter = loads(db_filter)
        try:
            result = yield c.c[c.database][c.collection].replace_one(db_filter, replacement, upsert=upsert)
            returnValue(dumps(DatabaseServer.UpdateResultToDict(result)))
        except Exception as e:
            print("Could not replace document matching filter {} in collection {} of database {}: {}".format(db_filter, c.collection, c.database, e))
            returnValue("{}")

    @setting(16, db_filter='s', update='s', upsert='b', returns='s')
    def update_one(self, c, db_filter, update, upsert=False):
        """
        update_one(self, c, db_filter, update, upsert=False)

        Update a single document matching ``db_filter`` with ``update``.
        
        See :py:meth:`pymongo.collection.Collection.update_one` for information on how ``db_filter`` (called ``filter`` in the documentation) and ``update`` work.

        Args:
            c: LabRAD context
            db_filter (str): BSON-dumped string of the filter
            update (str): BSON-dumped string of update
            upsert (bool, optional): Whether to create a document if none exists. Defaults to ``False``.

        Returns:
            str: A BSON-dumped string of the :py:class:`pymongo.results.UpdateResult`
        """
        update = loads(update)
        db_filter = loads(db_filter)
        try:
            result = yield c.c[c.database][c.collection].update_one(db_filter, update, upsert=upsert)
            returnValue(dumps(DatabaseServer.UpdateResultToDict(result)))
        except Exception as e:
            print("Could not update document matching filter {} in collection {} of database {}: {}".format(db_filter, c.collection, c.database, e))
            returnValue("{}")

    @setting(17, db_filter='s', update='s', upsert='b', returns='s')
    def update_many(self, c, db_filter, update, upsert=False):
        """
        update_many(self, c, db_filter, update, upsert=False)

        Update one or more documents matching ``db_filter`` with ``update``.
        
        See :py:meth:pymongo.collection.Collection.update_many for information on how ``db_filter`` (called ``filter`` in the documentation) and ``update`` work.

        Args:
            c: LabRAD context
            db_filter (str): BSON-dumped string of the filter
            update (str): BSON-dumped string of update
            upsert (bool, optional): Whether to create a document if none exists. Defaults to ``False``.

        Returns:
            str: A BSON-dumped string of the :py:class:`pymongo.results.UpdateResult`
        """
        update = loads(update)
        db_filter = loads(db_filter)
        try:
            result = yield c.c[c.database][c.collection].update_many(db_filter, update, upsert=upsert)
            returnValue(dumps(DatabaseServer.UpdateResultToDict(result)))
        except Exception as e:
            print("Could not update documents matching filter {} in collection {} of database {}: {}".format(db_filter, c.collection, c.database, e))
            returnValue("{}")

    @setting(18, db_filter='s', returns='s')
    def delete_one(self, c, db_filter):
        """
        delete_one(self, c, db_filter)

        Delete a single document matching ``db_filter``.
        
        See :py:meth:`pymongo.collection.Collection.delete_one` for information on how ``db_filter`` (called ``filter`` in the documentation) works.

        Args:
            c: LabRAD context
            db_filter (str): BSON-dumped string of the filter

        Returns:
            str: A BSON-dumped string of the :py:class:`pymongo.results.DeleteResult`
        """
        db_filter = loads(db_filter)
        try:
            result = yield c.c[c.database][c.collection].delete_one(db_filter)
            returnValue(dumps(DatabaseServer.DeleteResultToDict(result)))
        except Exception as e:
            print("Could not delete document matching filter {} in collection {} of database {}: {}".format(db_filter, c.collection, c.database, e))
            returnValue("{}")

    @setting(19, db_filter='s', returns='s')
    def delete_many(self, c, db_filter):
        """
        delete_many(self, c, db_filter)

        Delete one or more documents matching ``db_filter``.
        
        See the PyMongo documentation :py:meth:`pymongo.collection.Collection.delete_many` for information on how ``filter`` (called ``filter`` in the documentation) works.

        Args:
            c: LabRAD context
            db_filter (str): BSON-dumped string of the filter

        Returns:
            str: A BSON-dumped string of the :py:class:`pymongo.results.DeleteResult`
        """
        db_filter = loads(db_filter)
        try:
            result = yield c.c[c.database][c.collection].delete_many(db_filter)
            returnValue(dumps(DatabaseServer.DeleteResultToDict(result)))
        except Exception as e:
            print("Could not delete documents matching filter {} in collection {} of database {}: {}".format(db_filter, c.collection, c.database, e))
            returnValue("{}")

    @setting(20, db_filter='s', returns='s', projection='*s')
    def find_one(self, c, db_filter, projection=None):
        """
        find_one(self, c, db_filter, projection=None)

        Get a single document matching ``db_filter``.
        
        See :py:meth:`pymongo.collection.Collection.find_one` for information on how ``db_filter`` (called ``filter`` in the documentation) works.

        Args:
            c: LabRAD context
            db_filter (str): BSON-dumped string of the filter
            projection ([str]): a list of field names that should be returned in the result set. Defaults to ``None``, in which case all fields are returned.

        Returns:
            str: A BSON-dumped string of the document or ``{}`` if no document is found
        """
        db_filter = loads(db_filter)
        try:
            result = yield c.c[c.database][c.collection].find_one(db_filter, projection=projection)
            if result is not None:
                returnValue(dumps(result))
            else:
                returnValue("{}")
        except Exception as e:
            print("Could not find document matching filter {} in collection {} of database {}: {}".format(db_filter, c.collection, c.database, e))
            returnValue("{}")

if __name__ == '__main__':
    from labrad import util
    util.runServer(DatabaseServer())
