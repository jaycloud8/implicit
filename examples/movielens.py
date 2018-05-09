"""
An example based off the MovieLens 20M dataset.

This code will automatically download a HDF5 version of this
dataset when first run. The original dataset can be found here:
https://grouplens.org/datasets/movielens/.

Since this dataset contains explicit 5-star ratings, the ratings are
filtered down to positive reviews (4+ stars) to construct an implicit
dataset
"""

from __future__ import print_function

import argparse
import codecs
import logging
import time

import numpy as np

from implicit.als import AlternatingLeastSquares
from implicit.bpr import BayesianPersonalizedRanking
from implicit.nearest_neighbours import (BM25Recommender, CosineRecommender,
                                         TFIDFRecommender, bm25_weight)

from implicit.datasets.movielens import get_movielens


def calculate_similar_movies(output_filename,
                             model_name="als", min_rating=4.0):
    # read in the input data file
    start = time.time()
    titles, ratings = get_movielens()

    # remove things < min_rating, and convert to implicit dataset
    # by considering ratings as a binary preference only
    ratings.data[ratings.data < min_rating] = 0
    ratings.eliminate_zeros()
    ratings.data = np.ones(len(ratings.data))

    logging.info("read data file in %s", time.time() - start)

    # generate a recommender model based off the input params
    if model_name == "als":
        model = AlternatingLeastSquares()

        # lets weight these models by bm25weight.
        logging.debug("weighting matrix by bm25_weight")
        ratings = (bm25_weight(ratings,  B=0.9) * 5).tocsr()

    elif model_name == "bpr":
        model = BayesianPersonalizedRanking()

    elif model_name == "tfidf":
        model = TFIDFRecommender()

    elif model_name == "cosine":
        model = CosineRecommender()

    elif model_name == "bm25":
        model = BM25Recommender(B=0.2)

    else:
        raise NotImplementedError("TODO: model %s" % model_name)

    # train the model
    logging.debug("training model %s", model_name)
    start = time.time()
    model.fit(ratings)
    logging.debug("trained model '%s' in %s", model_name, time.time() - start)
    logging.debug("calculating top movies")

    user_count = np.ediff1d(ratings.indptr)
    to_generate = sorted(np.arange(len(titles)), key=lambda x: -user_count[x])

    with codecs.open(output_filename, "w", "utf8") as o:
        for movieid in to_generate:
            # if this movie has no ratings, skip over (for instance 'Graffiti Bridge' has
            # no ratings > 4 meaning we've filtered out all data for it.
            if ratings.indptr[movieid] == ratings.indptr[movieid + 1]:
                continue

            title = titles[movieid]
            for other, score in model.similar_items(movieid, 11):
                o.write("%s\t%s\t%s\n" % (title, titles[other], score))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates related movies from the MovieLens 20M "
                                     "dataset (https://grouplens.org/datasets/movielens/20m/)",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--output', type=str, default='similar-movies.tsv',
                        dest='outputfile', help='output file name')
    parser.add_argument('--model', type=str, default='als',
                        dest='model', help='model to calculate (als/bm25/tfidf/cosine)')
    parser.add_argument('--min_rating', type=float, default=4.0, dest='min_rating',
                        help='Minimum rating to assume that a rating is positive')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    calculate_similar_movies(args.outputfile,
                             model_name=args.model,
                             min_rating=args.min_rating)
