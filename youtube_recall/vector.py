#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import paddle.v2 as paddle
import argparse
import cPickle

from reader import Reader
from network_conf import DNNmodel
from utils import logger


def parse_args():
    """
    parse arguments
    :return:
    """
    parser = argparse.ArgumentParser(
        description="PaddlePaddle Youtube Recall Model Example")
    parser.add_argument(
        '--infer_set_path',
        type=str,
        required=True,
        help="path of the infer set")
    parser.add_argument(
        '--model_path', type=str, required=True, help="path of the model")
    parser.add_argument(
        '--feature_dict',
        type=str,
        required=True,
        help="path of feature_dict.pkl")
    parser.add_argument(
        '--batch_size',
        type=int,
        default=50,
        help="size of mini-batch (default:50)")
    return parser.parse_args()


def vector():
    """
    print user vector and item vector
    """
    args = parse_args()

    # check argument
    assert os.path.exists(
        args.infer_set_path), 'The infer_set_path path does not exist.'
    assert os.path.exists(
        args.model_path), 'The model_path path does not exist.'
    assert os.path.exists(
        args.feature_dict), 'The feature_dict path does not exist.'

    paddle.init(use_gpu=False, trainer_count=1)

    with open(args.feature_dict) as f:
        feature_dict = cPickle.load(f)

    nid_dict = feature_dict['history_clicked_items']
    nid_to_word = dict((v, k) for k, v in nid_dict.items())

    # load the trained model.
    with gzip.open(args.model_path) as f:
        parameters = paddle.parameters.Parameters.from_tar(f)

    # build model
    prediction_layer, fc = DNNmodel(
        dnn_layer_dims=[256, 31], feature_dict=feature_dict,
        is_infer=True).model_cost
    inferer = paddle.inference.Inference(
        output_layer=[prediction_layer, fc], parameters=parameters)

    reader = Reader(feature_dict)
    test_batch = []
    for idx, item in enumerate(reader.infer(args.infer_set_path)):
        test_batch.append(item)
        if len(test_batch) == args.batch_size:
            infer_a_batch(inferer, test_batch, nid_to_word)
            test_batch = []
    if len(test_batch):
        infer_a_batch(inferer, test_batch, nid_to_word)


def infer_a_batch(inferer, test_batch, nid_to_word):
    """
    input a batch of data and infer 
    """
    feeding = {
        'user_id': 0,
        'province': 1,
        'city': 2,
        'history_clicked_items': 3,
        'history_clicked_categories': 4,
        'history_clicked_tags': 5,
        'phone': 6
    }
    probs = inferer.infer(
        input=test_batch,
        feeding=feeding,
        field=["value"],
        flatten_result=False)
    for i, res in enumerate(zip(test_batch, probs[0], probs[1])):
        print "Sample %s:" % str(i)
        user_vector = [1.000]
        for i in res[2]:
            user_vector.append(i)
        user_vector.append(0.000)
        norm = np.linalg.norm(user_vector)
        user_vector_norm = [_ / norm for _ in user_vector]
        print user_vector_norm


if __name__ == "__main__":
    vector()
