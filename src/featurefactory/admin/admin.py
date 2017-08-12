import sys
import json
import yaml
import pandas as pd

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils import database_exists, create_database, drop_database

from featurehub.admin.sqlalchemy_declarative import (
    Base, Feature, Problem, User, Metric, EvaluationAttempt
)
from featurehub.admin.sqlalchemy_main import ORMManager
from featurehub.util import possibly_talking_action


class Commands(object):
    """Admin interface for the database.

    Create the schema, add or remove problems, and view problems, users, and
    features.
    """

    def __init__(self, problem=None, database="featurehub"):
        """Create the ORMManager and connect to DB.

        If problem name is given, load it.

        Parameters
        ----------
        problem : str, optional (default=None)
            Name of problem
        database : str, optional (default="featurehub")
            Name of database within DBMS.
        """

        self.__orm = ORMManager(database)

        if not database_exists(self.__orm.engine.url):
            print("database {} does not seem to exist.".format(database))
            print("You might want to create it by calling set_up method")
        elif  problem:
            try:
                with self.__orm.session_scope() as session:
                    problem = session.query(Problem)\
                                     .filter(Problem.name == problem).one()
                    self.__problemid = problem.id
            except NoResultFound:
                print("WARNING: Problem {} does not exist!".format(problem))
                print("You might want to create it by calling create_problem"
                      " method")

    def set_up(self, drop=False):
        """Create a new DB and create the initial scheme.

        If the database exists and drop=True, the existing database is dropped
        and recreated. Regardless, any tables defined by the schema that do not
        exist are created.

        Parameters
        ----------
        drop : bool, optional (default=False)
            Drop database if it already exists.
        """

        # todo extract database name from engine url and report for brevity
        engine = self.__orm.engine
        if database_exists(engine.url):
            print("Database {} already exists.".format(engine.url))
            if drop:
                print("Dropping old database {}".format(engine.url))
                drop_database(engine.url)
                with possibly_talking_action("Re-creating database..."):
                    create_database(engine.url)
        else:
            with possibly_talking_action("Creating database..."):
                create_database(engine.url)

        with possibly_talking_action("Creating tables..."):
            Base.metadata.create_all(engine)

        print("Database {} created successfully".format(engine.url))

    def bulk_create_problem_yml(self, path):
        """Create new problem entries in database from yml document stream.

        Can create a yml file with individual problems delimited into documents
        using the `---` ... `---` document stream syntax.

        Parameters
        ----------
        path: str or path-like
            Path to yml file
        """
        with open(path, "r") as f:
            obj_all = yaml.load_all(f)
            for obj in obj_all:
                self.create_problem(**obj)

    def create_problem_yml(self, path):
        """Create new problem entry in database from yml file.

        Parameters
        ----------
        path: str or path-like
            Path to yml file
        """
        with open(path, "r") as f:
            obj = yaml.load(f)

        self.create_problem(**obj)

    def create_problem(self, name="", problem_type="", problem_type_details={},
            data_dir_train="", data_dir_test="", files=[], table_names=[],
            entities_table_name="", entities_featurized_table_name="",
            target_table_name=""):
        """Creates new problem entry in database.

        Parameters
        ----------
        name : str
        problem_type : str
            Classification or regression
        problem_type_details : dict
            Dict with additional details about problem.
            For example, the dict may be {"classification_type" : "multiclass"}.
        data_dir_train : str
            Absolute path of containing directory of data files for training.
        data_dir_test : str
            Absolute path of containing directory of data files for testing
        files : list of str
            List of file paths relative to data_dir; files must be named
            identically within both data_dir directories.
        table_names : list of str
            List of table names, corresponding exactly to `files`
        entities_table_name : str
            Name of table that contains the entity variables. Must be found in
            `table_names`.
        entities_featurized_table_name : str
            Name of table that contains the pre-processed, featurized, entity
            variables. Must be found in `table_names`.
        target_table_name : str
            Name of table that contains the target variable (label). Must be
            found in table_names. Table must hold a single column with label
            values only.
        """

        with self.__orm.session_scope() as session:
            try:
                problem = session.query(Problem).filter(Problem.name == name).one()
                self.__problemid = problem.id
                print("Problem {} already exists".format(name))
                return
            except NoResultFound:
                pass    # we will create it

            problem = Problem(
                name                           = name,
                problem_type                   = problem_type,
                problem_type_details           = json.dumps(problem_type_details),
                data_dir_train                 = data_dir_train,
                data_dir_test                  = data_dir_test,
                files                          = json.dumps(files),
                table_names                    = json.dumps(table_names),
                entities_table_name            = entities_table_name,
                entities_featurized_table_name = entities_featurized_table_name,
                target_table_name              = target_table_name,
            )
            session.add(problem)
            self.__problemid = problem.id
            print("Problem {} successfully created".format(name))

    def get_problems(self):
        """Return a list of problems in the database."""

        with self.__orm.session_scope() as session:
            try:
                problems = session.query(Problem.name).all()
                return [problem[0] for problem in problems]
            except NoResultFound:
                return []

    def get_features(self, user_name=None):
        """Get a DataFrame with the details about all registered features."""
        with self.__orm.session_scope() as session:
            results = self._get_features(session, user_name).all()
            feature_dicts = []
            for feature, user_name in results:
                d = {
                    "user"        : user_name,
                    "description" : feature.description,
                    "md5"         : feature.md5,
                    "created_at"  : feature.created_at,
                }
                feature_metrics = session.query(Metric.name,
                        Metric.value).filter(Metric.feature_id ==
                                feature.id).all()
                # feature_metrics = feature.metrics
                for metric in feature_metrics:
                    d[metric.name] = metric.value

                feature_dicts.append(d)

            if not feature_dicts:
                print("No features found")
            else:
                return pd.DataFrame(feature_dicts)

    def _get_features(self, session, user_name=None):
        """Return a query filtering a given user for the current problem.

        Parameters
        ----------
        user_name : str, optional(default=None)
            If no user name provided, returns features for all users.
        """

        #TODO pivot metrics tables
        query = session.query(Feature, User.name)
        #query = session.query(Feature, User.name, Metric)

        if user_name:
            query = query.filter(User.name == user_name)

        query = query.filter(Feature.problem_id == self.__problemid)

        return query
