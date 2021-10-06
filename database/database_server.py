"""
Server for communicating with the MongoDB database

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
from pymongo import MongoClient
import json

class DatabaseServer(LabradServer):
    """
    Server for communicating with the MongoDB database
    """
    name = '%LABRADNODE%_database'

    @setting(9, server='s', port='s', user='s', password='s', database='s', collection='s', timeout='i', returns='s')
    def connect(self, c, server=None, port=None, user=None, password=None, database=None, collection=None, timeout=2000):
        """
        connect(self, c, server=None, port=None, user=None, password=None, database=None, collection=None)


        Args:
            c: LabRAD context
            server (str, optional): The server to connect to. Defaults to ``None``, in which case the server is loaded from ``mongodb.json`` if the file exists.
            port (str, optional): The port to connect to. Defaults to ``None``, in which case the port is loaded from ``mongodb.json`` if the file exists.
            user (str, optional): The user to connect as. Defaults to ``None``, in which case the user is loaded from ``mongodb.json`` if the file exists.
            password (str, optional): The user's password. Defaults to ``None``, in which case the password is loaded from ``mongodb.json`` if the file exists.
            database (str, optional): The database to select. Defaults to ``None``, in which case :meth:set_database must be run to set the client's context's database.
            collection (str, optional): The database's collection to select. Defaults to ``None``, in which case :meth:set_collection must be run to set the client's context's database's collection.
            timeout (int, optional): The timeout for connecting to the database (``connectTimeoutMS`` in the `PyMongo docs <https://pymongo.readthedocs.io/en/stable/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient>`__). Defaults to 2000.

        Returns:
            str: A JSON-dumped string of the result of `server_info() <https://pymongo.readthedocs.io/en/stable/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient.server_info>`__ if the connection was successful and the string "{}" otherwise.
        """
        client = MongoClient()
        try:
            return json.dumps(client.server_info())
        except Exception as e:
            return "{}"
        

    @setting(10)
    def close(self, c):
        """
        close(self, c)

        Close the client's context's connection to the database.

        Args:
            c: LabRAD context
        """
        pass

    @setting(11, database='s', returns='b')
    def set_database(self, c, database):
        """
        set_database(self, c, database)

        Sets the database associated with the client's context.

        Args:
            c: LabRAD context
            database (str): [description]

        Returns:
            bool: ``True`` if the database exists, ``False`` otherwise
        """
        
        pass

    @setting(12, collection='s', returns='b')
    def set_collection(self, c, collection):
        """
        set_collection(self, c, collection)

        Sets the collection associated with the client's context. :meth:set_database must already have been called.

        Args:
            c: LabRAD context
            collection (str): [description]

        Returns:
            bool: ``True`` if the collection exists in the current database, ``False`` otherwise
        """
        pass

    @setting(13, document='s', returns=str)
    def insert_one(self, c, document):
        """
        insert_one(self, c, document)

        Insert a single document.
        
        See `the PyMongo documentation <https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.insert_one>`__.

        Args:
            c: LabRAD context
            document (str): JSON-dumped string of the document

        Returns:
            str: A JSON-dumped string of the `InsertOneResult <https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html#pymongo.results.InsertOneResult>`__
        """
        pass

    @setting(14, documents='*s', ordered='b', returns=str)
    def insert_many(self, c, documents, ordered=True):
        """
        insert_many(self, c, documents, ordered=True)

        Inserts a list of documents.
        
        See `the PyMongo documentation <https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.insert_many>`__.

        Args:
            c: LabRAD context
            documents (list of str): list of JSON-dumped strings of the documents to insert
            ordered (bool, optional): If ``True`` (the default) documents will be inserted on the server serially, in the order provided. If an error occurs all remaining inserts are aborted. If ``False``, documents will be inserted on the server in arbitrary order, possibly in parallel, and all document inserts will be attempted.

        Returns:
            str: A JSON-dumped string of the `InsertManyResult <https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html#pymongo.results.InsertManyResult>`__
        """
        pass

    @setting(15, filter='s', update='s', upsert='b', returns=str)
    def replace_one(self, c, filter, update, upsert=False):
        """
        replace_one(self, c, filter, update, upsert=False)

        Replace a single document matching ``filter`` with ``update``.
        
        See `the PyMongo documentation <https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.update_one>`__ for information on how ``filter`` and ``update`` work.

        Args:
            c: LabRAD context
            filter (str): JSON-dumped string of the filter
            update (str): JSON-dumped string of update
            upsert (bool, optional): Whether to create a document if none exists. Defaults to ``False``.

        Returns:
            str: A JSON-dumped string of the `UpdateResult <https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html#pymongo.results.UpdateResult>`__
        """
        pass

    @setting(16, filter='s', update='s', upsert='b', returns=str)
    def update_one(self, c, filter, update, upsert=False):
        """
        update_one(self, c, filter, update, upsert=False)

        Update a single document matching ``filter`` with ``update``.
        
        See `the PyMongo documentation <https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.update_one>`__ for information on how ``filter`` and ``update`` work.

        Args:
            c: LabRAD context
            filter (str): JSON-dumped string of the filter
            update (str): JSON-dumped string of update
            upsert (bool, optional): Whether to create a document if none exists. Defaults to ``False``.

        Returns:
            str: A JSON-dumped string of the `UpdateResult <https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html#pymongo.results.UpdateResult>`__
        """
        pass

    @setting(17, filter='s', update='s', upsert='b')
    def update_many(self, c, filter, update, upsert=False):
        """
        update_many(self, c, filter, update, upsert=False)

        Update one or more documents matching ``filter`` with ``update``.
        
        See `the PyMongo documentation <https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.update_many>`__ for information on how ``filter`` and ``update`` work.

        Args:
            c: LabRAD context
            filter (str): JSON-dumped string of the filter
            update (str): JSON-dumped string of update
            upsert (bool, optional): Whether to create a document if none exists. Defaults to ``False``.

        Returns:
            str: A JSON-dumped string of the `UpdateResult <https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html#pymongo.results.UpdateResult>`__
        """
        pass

    @setting(18, filter='s', returns='s')
    def delete_one(self, c, filter):
        """
        delete_one(self, c, filter, update, upsert=False)

        Delete a single document matching ``filter``.
        
        See `the PyMongo documentation <https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.delete_one>`__ for information on how ``filter`` works.

        Args:
            c: LabRAD context
            filter (str): JSON-dumped string of the filter

        Returns:
            str: A JSON-dumped string of the `DeleteResult <https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html#pymongo.results.DeleteResult>`__
        """
        pass

    @setting(19, filter='s', returns='s')
    def delete_many(self, c, filter, update, upsert=False):
        """
        delete_many(self, c, filter, update, upsert=False)

        Delete one or more documents matching ``filter``.
        
        See `the PyMongo documentation <https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.delete_many>`__ for information on how ``filter`` works.

        Args:
            c: LabRAD context
            filter (str): JSON-dumped string of the filter

        Returns:
            str: A JSON-dumped string of the `DeleteResult <https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html#pymongo.results.DeleteResult>`__
        """
        pass

if __name__ == '__main__':
    from labrad import util
    util.runServer(DatabaseServer())
