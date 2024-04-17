import os
import gym
import sys
import json
import pickle
import string

import datetime
import random
from collections import Counter

import numpy as np
import requests

from gym.utils import seeding

from textwrap import dedent, indent

from llfbench.utils.parser_utils import SimpleGuidanceParser
from llfbench.envs.llf_env import Feedback


def get_details_via_omdb(title, verbose=False):
    url = "http://www.omdbapi.com/"

    try:
        api_key = os.environ['OMDB_API_KEY']
    except KeyError:
        api_key = input("Please enter your OMDB_API_KEY (follow README to register): ")
        if api_key.strip() == "":
            raise ValueError("Please provide a valid OMDB_API_KEY.")
        print("We have automatically set the OMDB_API_KEY environment variable for you.")

        os.environ['OMDB_API_KEY'] = api_key

    params = {
        "t": title,
        "apikey": api_key
    }

    response = requests.get(url, params=params)
    data = response.json()
    non_exist = True
    reviews = {}

    if "Error" in data:
        if verbose:
            print(data["Error"])
            print(title)
        return title, reviews, None, "PG", None, None, None, non_exist

    # allow fuzzy match
    # if data.get("Title") != title:
    #     return title, reviews, None, "PG", None, None, None, non_exist

    title = data.get("Title", title)
    genres = data.get("Genre", None)
    if genres is not None:
        genres = genres.split(",")
        genres = [g.strip() for g in genres]
    rating = data.get("Rated", None)
    production = data.get("Production", None)
    year = data.get("Year", None)

    show_type = data.get("Type", None)
    if show_type == "series":
        show_type = "show"

    if 'imdbRating' in data:
        reviews['imdbRating'] = data['imdbRating']
    if 'Ratings' in data:
        for item in data['Ratings']:
            if item['Source'] == 'Rotten Tomatoes':
                reviews['Rotten Tomatoes'] = item['Value']

    non_exist = False

    return title, reviews, genres, rating, production, year, show_type, non_exist


def verify_movie(title):
    """
    :param title:
    :return:
    """

    data = {'platform_monetization': [], 'title': "",
            "release_year": None, "type": None, "genre": [],
            "non_exist": False, 'IMDB': None, 'Rotten Tomatoes': None}

    title, reviews, genres, rating, production, year, show_type, non_exist = get_details_via_omdb(title)
    data['title'] = title
    data['genre'] = genres
    data['non_exist'] = non_exist  # if we found some info here, then it's still good

    if 'imdbRating' in reviews:
        if 'imdbRating' in reviews:
            if reviews['imdbRating'] != 'N/A':
                data['IMDB'] = float(reviews['imdbRating'])
            else:
                data['IMDB'] = 0
    if 'Rotten Tomatoes' in reviews:
        data['Rotten Tomatoes'] = int(reviews['Rotten Tomatoes'].strip('%'))

    # assert rating in ["PG-13", "R", "G", "PG", "NC-17"] or a TV rating!
    if not non_exist:
        if data['type'] == None and 'TV-' in rating:
            data['type'] = 'show'
        elif data['type'] == None and rating in ["PG-13", "R", "G", "PG", "NC-17"]:
            data['type'] = 'movie'

        if data['release_year'] == None:
            data['release_year'] = year

        if data['type'] == None:
            data['type'] = show_type

    data['child_friendly'] = rating in ["PG-13", "G", "PG"] or rating != 'TV-MA'
    data['adult_only'] = rating in ["R", "NC-17"] or rating == 'TV-MA'
    data['rating'] = rating
    data['production'] = production

    if data['release_year'] is not None:
        if '–' in data['release_year']:
            start_year, end_year = data['release_year'].split("–")
            if end_year != '':
                data['release_year'] = end_year
            else:
                # if no end year, we took the current year
                today = datetime.date.today()
                year = today.year
                data['release_year'] = year
        data['release_year'] = int(data['release_year'])

    return data


class RecommendationQueryGenerator:
    TYPES = ["movie", "TV show"]
    YEAR_RANGE = {
        "recent": "past few years",
        "2000s": "2000s",
        "90s": "90s",
        "80s": "80s",
    }
    GENRES = ['Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime', 'Documentary', 'Drama',
              'Fantasy', 'Film Noir', 'History', 'Horror', 'Musical', 'Mystery', 'Romance', 'Sci-Fi',
              'Sport', 'Superhero', 'Thriller', 'War', 'Western']
    AGE_RESTRICTED = ["child-friendly", "R-rated", "family-friendly"]

    def __init__(self, seed=None):
        self._seed = self.seed(seed)

    def seed(self, seed=None):
        """Seed the PRNG of this space and possibly the PRNGs of subspaces."""
        self._np_random, seed = seeding.np_random(seed)
        return [seed]

    def generate_random_profile(self):
        profile = {
            "type_": self._np_random.choice(self.TYPES),
            "year_ranges": self._np_random.choice(list(self.YEAR_RANGE.keys()), self._np_random.integers(0, 2+1)).tolist(),  # len(cls.YEAR_RANGE)
            "genre": self._np_random.choice(self.GENRES, self._np_random.integers(0, 2+1)).tolist(),  # len(cls.GENRES)  # Include None as an option
            "age_restriction": self._np_random.choice([None] + self.AGE_RESTRICTED, 1, p=[0.4, 0.2, 0.2, 0.2]).tolist()[0],
            "sampled_start_exp_idx": self._np_random.integers(0, 9+1),
            "sampled_end_exp_idx": self._np_random.integers(0, 4+1)
        }

        # child-friendly and family-friendly should not be selected in the following genres:
        not_child_friendly_genres = ['Crime', 'War', 'Romance']
        if len(set(profile['genre']).intersection(set(not_child_friendly_genres))) > 0:
            profile['age_restriction'] = None

        not_adult_only_genres = ['History', 'Biography', 'Documentary',
                                 'Sport', 'Musical']
        if len(set(profile['genre']).intersection(set(not_adult_only_genres))) > 0:
            profile['age_restriction'] = None

        partial_profile = {
            'type_': profile['type_'],
            'sampled_start_exp_idx': profile['sampled_start_exp_idx'],
            'sampled_end_exp_idx': profile['sampled_end_exp_idx']
        }
        non_empty_keys = [k for k, v in profile.items() if v is not None and v != [] and k not in partial_profile]
        # we randomly occlude one attribute
        hid_key = self._np_random.choice(non_empty_keys)

        for k, v in profile.items():
            if k != hid_key:
                partial_profile[k] = v

        return profile, partial_profile

    def _get_a_or_an(self, word):
        vowels = "AEIOUaeiou"
        return "an" if word[0] in vowels else "a"

    def _list_to_string(self, items_list, separator=', ', last_separator=' or ', oxford_comma=True):
        if items_list is None or items_list is False:
            return ""

        if len(items_list) == 1:
            return items_list[0]

        if oxford_comma:
            return separator.join(items_list[:-1]) + ',' + last_separator + items_list[-1]
        else:
            return separator.join(items_list[:-1]) + last_separator + items_list[-1]

    def generate_query(self, type_=None, year_ranges=[], genre=[],
                       age_restriction=None, sampled_start_exp_idx=None, sampled_end_exp_idx=None):

        genre_text = "" if len(genre) == 0 else " " + self._list_to_string(genre, oxford_comma=False, last_separator=' and ')
        age_res_text = "" if age_restriction is None else " " + age_restriction

        expressions = [
            f"Hey, I'm in the mood for a good{age_res_text}{genre_text} {type_}. Any suggestions",
            f"Can you recommend some{age_res_text}{genre_text} {type_}s",
            f"I love{genre_text} {type_}s! Can you recommend a few{age_res_text} {type_}s",
            f"I'm a big fan of{genre_text} {type_}s. Do you have any{age_res_text} {type_} recommendations for me",
            f"I'm trying to get into{genre_text} {type_}s. Can you suggest some must-watch{age_res_text} {type_}",
            f"What are the top{age_res_text}{genre_text} {type_}s out there right now",
            f"I've been craving some great{age_res_text}{genre_text} {type_}s",
            f"Hit me with your best{age_res_text}{genre_text} {type_} suggestions",
            f"Help me find a new favorite{age_res_text}{genre_text} {type_}",
            f"Looking for some iconic{age_res_text}{genre_text} {type_}s"
        ]

        end_phrases = ["", " Where should I start?", " Please point me in the right direction.",
                       " Any pointers?", " Got any ideas?"]

        base_query = random.choice(expressions) if sampled_start_exp_idx is None else expressions[sampled_start_exp_idx]
        sampled_start_exp_idx = expressions.index(base_query)

        end_phrase = random.choice(end_phrases) if sampled_end_exp_idx is None else end_phrases[sampled_end_exp_idx]

        # Ensure the genre has the right article (a/an)
        if "a good {genre}" in base_query:
            base_query = base_query.replace("a good", f"{self._get_a_or_an(genre)} good")

        # Year range
        if year_ranges:
            formatted_years = self._list_to_string([self.YEAR_RANGE[yr] for yr in year_ranges], oxford_comma=False)
            base_query += f" from the {formatted_years}"

        if sampled_start_exp_idx in [0, 1, 2, 3, 4, 5]:
            base_query += f'?{end_phrase}'
        else:
            base_query += f'.{end_phrase}'

        return base_query


class RecContentExtractor(object):
    # use LLM to extract the poem
    # just in case more things were written
    def __init__(self, llm, silent=True):
        self.llm = llm
        self.prompt = SimpleGuidanceParser(dedent("""
        {{#system~}}
        You are a helpful assistant.
        {{~/system}}

        {{#user~}}

        Extract the movies and additional information from the following generated content:
        ```
        {{content}}
        ```
        into a JSON format that looks like this:
        ```
        [{"title": "movie1"},
         {"title": "movie2"}]
        ```
        You must output a valid JSON:
        {{~/user}}

        {{#assistant~}}
        {{gen 'content' temperature=0}}
        {{~/assistant}}
        """))

    def __call__(self, content):
        messages = self.prompt(content=content)
        response, info = self.llm.generate(messages)
        return response


class MovieRec(gym.Env):
    YEAR_RANGE = {
        "recent": "past few years",
        "2000s": "2000s",
        "90s": "90s",
        "80s": "80s",
    }
    def __init__(self, feedback=0, seed=None,
                 cached_data='factual_movie_data_2023_12_16.pkl',
                 instruction_type='c'):
        super().__init__()

        self.instruction_type = instruction_type

        self.feedback_level = feedback
        assert self.feedback_level in {0, 0.5, 1}

        self.extractor = None
        self.query_generator = RecommendationQueryGenerator(seed=seed)

        self.profile = None
        self.partial_profile = None

        self.action_space = gym.spaces.Text(sys.maxsize, charset=string.printable)
        self.observation_space = gym.spaces.Text(sys.maxsize, charset=string.printable)

        self.is_first_order_feedback = self.feedback_level == 1

        self.reward_range = (0, 1)

        file_path = os.path.dirname(os.path.abspath(__file__))
        self.cached_movie_data = pickle.load(open(os.path.join(file_path, cached_data), "rb"))
        self.cached_movie_data_shuffled = list(self.cached_movie_data.items())

        self.docstring = dedent("""
        You are a helpful assistant trying to recommend movies to your users according to what they want.

        Sometimes, your users don't fully tell you their preferences at the start, but once you make recommendations,
        they will tell you truthfully what they like and don't like.

        Please produce a valid json list with a dictionary: [{"title": "movie1"}, {"title": "movie2"}]
        """)

    def seed(self, seed=None):
        """Seed the PRNG of this space and possibly the PRNGs of subspaces."""
        self.query_generator = RecommendationQueryGenerator(seed=seed)
        random.seed(seed)
        self._np_random, seed = seeding.np_random(seed)
        return [seed]

    def initialize_text_extractor(self, content_extractor: RecContentExtractor):
        self.extractor = content_extractor

    def generate_request_query(self, profile):
        return self.query_generator.generate_query(**profile)

    def reset(self, **kwargs):
        if 'seed' in kwargs:
            self._seed = self.seed(kwargs['seed'])
            self.query_generator = RecommendationQueryGenerator(seed=kwargs['seed'])
            random.seed(self._seed)

        rand_profile, partial_profile = self.query_generator.generate_random_profile()
        self.profile = rand_profile
        self.partial_profile = partial_profile

        random.shuffle(self.cached_movie_data_shuffled)

        # Profile:
        # {'type_': 'TV show',
        #  'year_ranges': ['recent', '2000s', '80s'],
        #  'genre': 'Documentary',
        #  'age_restriction': 'child-friendly'}

        # profile is fixed
        # however, we can choose to partially hide some part of profile in the initial query
        # and reveal profile gradually in the feedback (through likes/dislikes, or explicit request)

        if self.instruction_type == 'c':
            profile = self.profile
        elif self.instruction_type == 'b':
            profile = self.partial_profile
        else:
            raise Exception("Instruction type not supported")

        return self.generate_request_query(profile)

    def extract_with_retry(self, a):
        retry = 3
        rec_movies = None

        while retry > 0:
            try:
                a = self.extractor(a)
                # we can add a retry here if json fails to parse
                rec_movies = json.loads(a)
                assert type(rec_movies) == list
                assert "title" in rec_movies[0].keys()
                break
            except:
                retry -= 1

        return rec_movies

    def sample_success_by_year(self, profile_years):
        success_items, error_items = [], []
        for title, data in self.cached_movie_data_shuffled:
            if self.map_type(data['type']) != self.profile['type_']:
                continue
            if self.check_movie_year(data['release_year'], profile_years):
                success_items.append((title, data['release_year']))
            else:
                error_items.append((title, data['release_year']))

            if len(success_items) >= 2 and len(error_items) >= 2:
                break

        return success_items[:2], error_items[:2]

    def sample_success_by_genres(self, profile_genres):
        success_items, error_items = [], []
        for title, data in self.cached_movie_data_shuffled:
            if self.map_type(data['type']) != self.profile['type_']:
                continue
            if self.check_movie_genre(data['genre'], profile_genres):
                success_items.append((title, data['genre']))
            else:
                error_items.append((title, data['genre']))

            if len(success_items) >= 2 and len(error_items) >= 2:
                break

        return success_items[:2], error_items[:2]

    def sample_success_by_age_restriction(self, profile_age_restriction):
        success_items, error_items = [], []
        for title, data in self.cached_movie_data_shuffled:
            if self.map_type(data['type']) != self.profile['type_']:
                continue
            if profile_age_restriction in {'child-friendly', 'family-friendly'}:
                if data['child_friendly'] is True:
                    success_items.append(title)
            elif profile_age_restriction == 'R-rated':
                if data['adult_only'] is True:
                    success_items.append(title)

            if len(success_items) >= 2 and len(error_items) >= 2:
                break

        return success_items[:2], error_items[:2]

    def sample_success_by_type(self, pref_type):
        success_items, error_items = [], []
        for title, data in self.cached_movie_data_shuffled:
            if self.map_type(data['type']) == pref_type:
                success_items.append((title, self.map_type(data['type'])))
            else:
                error_items.append((title, self.map_type(data['type'])))

            if len(success_items) >= 2 and len(error_items) >= 2:
                break

        return success_items[:2], error_items[:2]

    def _list_to_string(self, items_list, separator=', ', last_separator=' or '):
        if not items_list:
            return ""

        if len(items_list) == 1:
            return items_list[0]

        return separator.join(items_list[:-1]) + ',' + last_separator + items_list[-1]

    def check_movie_year(self, movie_year, profile_years):
        # because we got rid of hallucinations before
        # now everything is fine if we have missing data
        if movie_year is None:
            return True

        checks = []
        for profile_year in profile_years:
            if profile_year == '80s':
                checks += [movie_year >= 1980 and movie_year <= 1989]
            elif profile_year == '90s':
                checks += [movie_year >= 1990 and movie_year <= 1999]
            elif profile_year == '2000s':
                checks += [movie_year >= 2000 and movie_year <= 2009]
            elif profile_year == 'recent':
                checks += [movie_year >= 2010]
            else:
                raise ValueError(f"Invalid profile year: {profile_year}")

        success = any(checks)

        return success

    def check_movie_genre(self, movie_genres, profile_genres):
        if movie_genres is None:
            return True

        checks = []
        # set constraint -- movie's genre should appear in the profile
        # but it can go over it
        # for example, movie = ['action', 'comedy'], profile = ['action']
        # it still counts as satisfactory
        for movie_genre in movie_genres:
            checks += [movie_genre in profile_genres]

        success = any(checks)

        return success

    def combine_platforms(self, platform):
        if platform in {'Netflix', 'Netflix basic with Ads'}:
            return "Netflix"
        else:
            return platform

    def check_year(self, factual_movie_data, profile_years, first_order=False):
        error_items = []
        success_items = []
        for title, factual_info in factual_movie_data.items():
            movie_year = factual_info['release_year']
            success = self.check_movie_year(movie_year, profile_years)
            if not success:
                error_items.append((title, movie_year))
            else:
                success_items.append((title, movie_year))

        correct_years = self._list_to_string([self.YEAR_RANGE[year] for year in profile_years])

        if len(error_items) == 0:
            didactic_feedback = Feedback(
                r=f"The recommended movies are all from the {correct_years}, great!")
            return True, None, didactic_feedback, {'unsatisfied': []}

        feedback = f"The recommended {self.profile['type_']}s are not from the {correct_years}."
        didactic_feedback = Feedback(r=feedback)

        if first_order:
            for item in error_items:
                feedback += f" {item[0]} is from {item[1]}."
            feedback += f" I want {self.profile['type_']}s from the {correct_years}."

        if len(success_items) > 0:
            hp = f"These {self.profile['type_']}s are indeed from the {correct_years}:"
            for item in success_items:
                hp += f" {item[0]} is from {item[1]},"
            didactic_feedback.hp = hp

        if len(error_items) > 0:
            hn = f"These {self.profile['type_']}s are not from the {correct_years}:"
            for item in error_items:
                hn += f" {item[0]} is from {item[1]},"
            didactic_feedback.hn = hn

        success_items, error_items = self.sample_success_by_year(profile_years)
        success_items, error_items = list(set(success_items)), list(set(error_items))

        fp = f"Recommend {self.profile['type_']}s that are from {correct_years}, like "
        fp += self._list_to_string([i[0] for i in success_items], last_separator=' and ')
        fp += '.'

        didactic_feedback.fp = fp

        fn = f"Do not recommend {self.profile['type_']}s that are not from {correct_years}, like "
        fn += self._list_to_string([i[0] for i in error_items], last_separator=' or ')
        fn += '.'
        didactic_feedback.fn = fn

        return False, feedback, didactic_feedback, {"unsatisfied": [item[0] for item in error_items]}

    def check_genre(self, factual_movie_data, profile_genres, first_order=False):
        success_items, error_items = [], []
        for title, factual_info in factual_movie_data.items():
            movie_genres = factual_info['genre']
            success = self.check_movie_genre(movie_genres, profile_genres)
            if not success:
                error_items.append((title, movie_genres))
            else:
                success_items.append((title, movie_genres))

        if len(error_items) == 0 and len(success_items) > 0:
            didactic_feedback = Feedback(
                r=f"The recommended {self.profile['type_']}s are all {self._list_to_string(profile_genres, last_separator=' and ')}, nice!")
            return True, None, didactic_feedback, {'unsatisfied': []}

        feedback = f"The recommendations are not all {self._list_to_string(profile_genres, last_separator=' and ')} {self.profile['type_']}s."

        didactic_feedback = Feedback(r=feedback)

        if first_order:
            for item in error_items:
                feedback += f" {item[0]} is {self._list_to_string(item[1])}."
            feedback += f" I want {self.profile['type_']}s that are {self._list_to_string(profile_genres, last_separator=' and ')}."

        if len(success_items) > 0:
            hp = f"These {self.profile['type_']}s are indeed {self._list_to_string(profile_genres, last_separator=' and ')}:"
            for item in success_items:
                hp += f" {item[0]} is {self._list_to_string(item[1])},"
            didactic_feedback.hp = hp

        if len(error_items) > 0:
            hn = f"These {self.profile['type_']}s are not {self._list_to_string(profile_genres, last_separator=' and ')}:"
            for item in error_items:
                hn += f" {item[0]} is {self._list_to_string(item[1])},"
            didactic_feedback.hn = hn

        success_items, error_items = self.sample_success_by_genres(profile_genres)

        fp = f"Recommend {self.profile['type_']}s that are {self._list_to_string(profile_genres, last_separator=' and ')}, like "
        fp += self._list_to_string([i[0] for i in success_items], last_separator=' and ')
        fp += '.'
        didactic_feedback.fp = fp

        fn = f"Do not recommend {self.profile['type_']}s that are not {self._list_to_string(profile_genres, last_separator=' and ')}, not like "
        fn += self._list_to_string([i[0] for i in error_items], last_separator=' or ')
        fn += '.'
        didactic_feedback.fn = fn

        return False, feedback, didactic_feedback, {"unsatisfied": [item[0] for item in error_items]}

    def translate_watch_options(self, option):
        if option in {'flatrate', "ads", "free"}:
            return 'stream'
        else:
            return option

    def map_type(self, type_):
        if type_ is None:
            return 'movie'

        if type_.lower() == 'movie':
            return 'movie'
        elif type_.lower() == 'show':
            return 'TV show'
        else:
            raise ValueError(f"Invalid type: {type_}")

    def check_type(self, factual_movie_data, profile_type, first_order=False):
        # is it even a movie or a tv show

        error_items, success_items = [], []
        for title, factual_info in factual_movie_data.items():
            if self.map_type(factual_info['type']) != profile_type:
                error_items.append((title, self.map_type(factual_info['type'])))
            else:
                success_items.append((title, self.map_type(factual_info['type'])))

        if len(error_items) == 0 and len(success_items) > 0:
            didactic_feedback = Feedback(
                r=f"What you recommended are {self.profile['type_']}s, nice!")
            return True, None, didactic_feedback, {'unsatisfied': []}
        elif  len(error_items) == 0 and len(success_items) == 0:
            didactic_feedback = Feedback(
                r=f"What you recommended are not {self.profile['type_']}s!")
            return True, None, didactic_feedback, {'unsatisfied': []}
        else:
            feedback = self._list_to_string([e[0] for e in error_items], last_separator=' and ')
            feedback += self.plural_wrap(profile_type, len(error_items)) + '.'

            if first_order:
                feedback += f" Please suggest {profile_type}s instead."

            didactic_feedback = Feedback(
                r=f"The recommended items are not all {profile_type}s.")

            if len(success_items) > 0:
                hp = f"These items are indeed all {profile_type}s:"
                for item in success_items:
                    hp += f" {item[0]},"
                didactic_feedback.hp = hp

            if len(error_items) > 0:
                hn = f"These items are not all {profile_type}s:"
                for item in error_items:
                    hn += f" {item[0]} is {item[1]},"
                didactic_feedback.hn = hn

            success_items, error_items = self.sample_success_by_type(profile_type)
            fp = f"Recommend {profile_type}s, like "
            # for item in success_items:
            #     fp += f" {item[0]},"
            fp += self._list_to_string([i[0] for i in success_items], last_separator=' and ')
            fp += '.'
            didactic_feedback.fp = fp

            fn = f"Do not recommend items that are not {profile_type}s, like "
            # for item in error_items:
            #     fn += f" {item[0]},"
            fn += self._list_to_string([i[0] for i in error_items], last_separator=' or ')
            fn += '.'
            didactic_feedback.fn = fn

            return False, feedback, didactic_feedback, {'unsatisfied': error_items}

    def plural_wrap(self, text, count):
        if count > 1:
            return " are not " + text + 's'
        else:
            return " is not a " + text

    def check_child_friendly(self, factual_movie_data, profile_age_restriction, profile_type, first_order=False):

        if profile_age_restriction is None:
            return True, None, {'unsatisfied': []}

        error_items, success_items = [], []
        for title, factual_info in factual_movie_data.items():
            if profile_age_restriction in {'child-friendly', 'family-friendly'}:
                if factual_info['child_friendly'] is False:
                    error_items.append(title)
                else:
                    success_items.append(title)
            elif profile_age_restriction == 'R-rated':
                if factual_info['adult_only'] is False:
                    error_items.append(title)
                else:
                    success_items.append(title)

        if len(error_items) == 0:
            didactic_feedback = Feedback(
                r=f"The recommended {self.profile['type_']}s are all {profile_age_restriction}, awesome!")
            return True, None, didactic_feedback, {'unsatisfied': []}
        else:
            feedback = self._list_to_string(error_items)
            feedback += self.plural_wrap(f"{profile_age_restriction} {profile_type}", len(error_items))

            if first_order:
                feedback += f" Please suggest {profile_age_restriction} {profile_type}s instead."

            didactic_feedback = Feedback(
                r=f"The recommended {self.profile['type_']}s are not all {profile_age_restriction}.")

            if len(success_items) > 0:
                hp = f"These {self.profile['type_']}s are indeed {profile_age_restriction}:"
                for item in success_items:
                    hp += f" {item},"
                didactic_feedback.hp = hp

            if len(error_items) > 0:
                hn = f"These {self.profile['type_']}s are not {profile_age_restriction}:"
                for item in error_items:
                    hn += f" {item},"
                didactic_feedback.hn = hn

            success_items, error_items = self.sample_success_by_age_restriction(profile_age_restriction)

            fp = f"Recommend {self.profile['type_']}s that are {profile_age_restriction}, like "
            # for item in success_items:
            #     fp += f" {item},"
            fp += self._list_to_string(success_items, last_separator=' and ')
            fp += '.'
            didactic_feedback.fp = fp

            fn = f"Do not recommend {self.profile['type_']}s that are not {profile_age_restriction}, like "
            # for item in error_items:
            #     fn += f" {item[0]},"
            fn += self._list_to_string(error_items, last_separator=' or ')
            fn += '.'
            didactic_feedback.fn = fn

            return False, feedback, didactic_feedback, {'unsatisfied': error_items}

    def check_hallucination(self, factual_movie_data, first_order=False):
        error_items, success_items = [], []
        for title, factual_info in factual_movie_data.items():
            if factual_info['non_exist'] is True:
                error_items.append(title)
            else:
                success_items.append(title)

        if len(error_items) == 0:
            didactic_feedback = Feedback(r=f"I can find all the recommended {self.profile['type_']}s, nice!")
            return True, None, didactic_feedback, {'unsatisfied': []}
        else:
            feedback = "I can't find " + self._list_to_string(error_items) + " on the internet."
            # feedback += self.plural_wrap(f"real {self.profile['type_']}", len(items))

            if first_order:
                feedback += f" Are they even real? Please suggest {self.profile['type_']}s that actually exist."

            didactic_feedback = Feedback(
                r=f"I can't find some of the recommended {self.profile['type_']}s on the internet.")

            if len(success_items) > 0:
                hp = f"I can find these {self.profile['type_']}s on the internet:"
                for item in success_items:
                    hp += f" {item},"
                didactic_feedback.hp = hp

            if len(error_items) > 0:
                hn = f"I can't find these {self.profile['type_']}s on the internet:"
                for item in error_items:
                    hn += f" {item},"
                didactic_feedback.hn = hn

            fp = f"Recommend {self.profile['type_']}s that I can find online, like: "
            for item in success_items:
                fp += f" {item},"
            fp += '.'
            didactic_feedback.fp = fp

            fn = f"Do not recommend {self.profile['type_']}s that I can't find online, like: "
            for item in error_items:
                fn += f" {item},"
            fn += '.'
            didactic_feedback.fn = fn

            return False, feedback, didactic_feedback, {'unsatisfied': error_items}

    def generate_feedback(self, rec_movie_data):
        # this is the utterance after receiving the recommendation
        # the user will comment on each movie, and say whether they like or dislike it
        # based on their profile (which can be partially missing in their request query)

        # format should be : {'title': "", 'year': "", platform: "", genre: ""}
        factual_movie_data = {}

        for movie_tup in rec_movie_data:
            title = movie_tup['title']
            if title in self.cached_movie_data:
                factual_movie_data[title] = self.cached_movie_data[title]
            else:
                factual_movie_data[title] = verify_movie(title)

        feedbacks, didactic_feedbacks, bad_recs = [], {}, []
        # now we check each movie one by one to see if they match our profile
        # if not, we list the reasons why

        # we first check hallucinated movies, and remove them from the list already (add to bad_recs)
        success, feedback, didactic_feedback, info = self.check_hallucination(factual_movie_data,
                                                                              first_order=self.is_first_order_feedback)
        feedbacks.append(feedback)
        didactic_feedbacks['hallucination'] = didactic_feedback
        bad_recs.extend(info['unsatisfied'])
        # remove bad_recs from factual_movie_data (we don't want to check them again)
        for bad_rec in bad_recs:
            del factual_movie_data[bad_rec]

        if len(factual_movie_data) == 0:
            # all hallucinations
            title_to_num_rules_violation = Counter(bad_recs)
            return 0, feedbacks, didactic_feedbacks, title_to_num_rules_violation

        # we do checks line by line
        # if it's a movie or tv show
        success, feedback, didactic_feedback, info = self.check_type(factual_movie_data, self.profile['type_'],
                                                                     first_order=self.is_first_order_feedback)
        feedbacks.append(feedback)
        didactic_feedbacks['type'] = didactic_feedback
        bad_recs.extend(info['unsatisfied'])

        # if it's in the genre
        if len(self.profile['genre']) > 0:
            success, feedback, didactic_feedback, info = self.check_genre(factual_movie_data, self.profile['genre'],
                                                                          first_order=self.is_first_order_feedback)
            feedbacks.append(feedback)
            didactic_feedbacks['genre'] = didactic_feedback
            bad_recs.extend(info['unsatisfied'])

        # if it's in the year
        if len(self.profile['year_ranges']) > 0:
            success, feedback, didactic_feedback, info = self.check_year(factual_movie_data,
                                                                         self.profile['year_ranges'],
                                                                         first_order=self.is_first_order_feedback)
            feedbacks.append(feedback)
            didactic_feedbacks['year'] = didactic_feedback
            bad_recs.extend(info['unsatisfied'])

        # if it's child-friendly
        if self.profile['age_restriction'] is not None:
            success, feedback, didactic_feedback, info = self.check_child_friendly(factual_movie_data,
                                                                                   self.profile['age_restriction'],
                                                                                   self.profile['type_'],
                                                                                   first_order=self.is_first_order_feedback)
            feedbacks.append(feedback)
            didactic_feedbacks['child_friendly'] = didactic_feedback
            bad_recs.extend(info['unsatisfied'])

        # we should compute a numerical score
        total_num_movies = len(factual_movie_data)
        title_to_num_rules_violation = Counter(bad_recs)
        # we also count how many rules a movie violates
        bad_recs = title_to_num_rules_violation.keys()

        if total_num_movies != 0:
            reward = 1 - len(bad_recs) / total_num_movies
        else:
            reward = 0

        feedbacks = [f for f in feedbacks if f is not None]

        # title_to_num_rules_violation:
        # Counter({'Made up movie 1': 1, 'Made up movie 2': 1})

        return reward, feedbacks, didactic_feedbacks, title_to_num_rules_violation

    def step(self, a):
        # observation, reward, terminal, info

        # currently this is not designed for multi-turn
        # but "original_feedback" can be the next observation if we so desire!

        profile = self.profile if self.instruction_type == 'c' else self.partial_profile

        if self.profile is None:
            raise Exception("Must call env.reset() before calling env.step()")

        if self.extractor is None and type(a) != list:
            try:
                a = eval(a)
            except:
                didactic_feedback = Feedback()
                didactic_feedback.r = f'You entered an action with invalid format: {a}'
                didactic_feedback.fp = didactic_feedback.r + """ Please produce a valid json list with a dictionary: [{"title": "movie1"}, {"title": "movie2"}]"""
                return None, 0, True, {'success': False, 'feedback': didactic_feedback, "original_feedback": didactic_feedback.fp}

        if type(a) != list or 'title' not in a[0]:
            didactic_feedback = Feedback()
            didactic_feedback.r = f'You entered an action with invalid format: {a}'
            didactic_feedback.fp = didactic_feedback.r + """ Please produce a valid json list with a dictionary: [{"title": "movie1"}, {"title": "movie2"}]"""
            return None, 0, True, {'success': False, 'feedback': didactic_feedback,
                                   "original_feedback": didactic_feedback.fp}
        rec_movies = a

        if rec_movies is None:
            # there's no difference between observation and feedback?
            return self.generate_request_query(profile), 0, False, {"raw_action": a,
                                                             "original_feedback": "You didn't recommend anything to me.",
                                                             'feedback': {"no_rec": Feedback(
                                                                 r="You didn't recommend anything to me.")},
                                                             "item_errors": {},
                                                             'success': False}

        # 0-th order: just say whichever ones didn't satisfy the profile
        # 0.5-th order: explain why it didn't satisfy the criteria
        # 1st order: explain why it didn't satisfy the critiera, and ask for a recommendation that satisfies the critiera

        reward, feedbacks, didactic_feedbacks, title_to_num_rules_violation = self.generate_feedback(rec_movies)

        if len(feedbacks) == 0:
            initial_feedback = "Thank you! I like all of these recommendations."
            return self.generate_request_query(profile), reward, False, {"raw_action": a, "original_feedback": initial_feedback,
                                                                  'feedback': didactic_feedbacks,
                                                                  "item_errors": title_to_num_rules_violation,
                                                                  'success': True}

        initial_feedback = "These recommendations are not what I wanted. Can you give me some new recommendations?\n"

        if self.feedback_level == 0:
            return self.generate_request_query(profile), reward, False, {"raw_action": a,
                                                                  "original_feedback": initial_feedback,
                                                                  'feedback': didactic_feedbacks,
                                                                  "item_errors": title_to_num_rules_violation,
                                                                  'success': False}
        else:
            initial_feedback += "\n".join(feedbacks)
            return self.generate_request_query(profile), reward, False, {"raw_action": a,
                                                                  "original_feedback": initial_feedback,
                                                                  'feedback': didactic_feedbacks,
                                                                  "item_errors": title_to_num_rules_violation,
                                                                  'success': False}


def test_generate_query():
    # Example usage:
    generator = RecommendationQueryGenerator()
    # "80s", "90s"
    query = generator.generate_query(platforms=["Netflix", "YouTube", "HBO Max"], type_="movie",
                                     year_ranges=["recent"], options=["stream"], genre=["Action", "Comedy"])
    print(query)

    rand_profile = generator.generate_random_profile()
    query = generator.generate_query(**rand_profile)
    print(query)


def test_environment():
    env = MovieRec(feedback=0.5)
    obs = env.reset()
    print(obs)
    a = """[
      {"title": "John Wick", "year": "2014", "platform": "Netflix", "genre": "action"},
      {"title": "Mad Max: Fury Road", "year": "2015", "platform": "Netflix", "genre": "action"},
      {"title": "Baby Driver", "year": "2017", "platform": "Netflix", "genre": "action"},
      {"title": "Avengers: Infinity War", "year": "2018", "platform": "Netflix", "genre": "action"},
      {"title": "Mission: Impossible - Fallout", "year": "2018", "platform": "Hulu/HBO Max", "genre": "action"},
      {"title": "Extraction", "year": "2020", "platform": "Netflix", "genre": "action"},
      {"title": "Wonder Woman", "year": "2017", "platform": "Netflix", "genre": "action"},
      {"title": "The Raid: Redemption", "year": "2011", "platform": "YouTube", "genre": "action"},
      {"title": "The Dark Knight", "year": "2008", "platform": "Netflix", "genre": "action"},
      {"title": "The Old Guard", "year": "2020", "platform": "Netflix", "genre": "action"}
    ]"""
    import json
    a = json.loads(a)
    obs, rew, _, info = env.step(a)

    print(rew)
    print(info['feedback'])
    print(info['feedback'])


if __name__ == '__main__':
    # test_generate_query()
    test_environment()
