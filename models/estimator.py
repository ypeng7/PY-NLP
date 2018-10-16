#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dataset, Estimator API of Tensorflow

# @Date    : 2018-10-13
# @Author  : Yue Peng (ypeng7@outlook.com)
"""
import sys, os
import tensorflow as tf
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)))
from utils.log import getLogger


logger = getLogger(__name__)


# Set default flags for the output directories
# FLAGS = tf.app.flags.FLAGS
# tf.app.flags.DEFINE_string(
#     flag_name="model_dir", default_value="./py", docstring="Output directory for model and training stats.")

PREDICT = tf.estimator.ModeKeys.PREDICT
EVAL = tf.estimator.ModeKeys.EVAL
TRAIN = tf.estimator.ModeKeys.TRAIN


parser = argparse.ArgumentParser()
parser.add_argument(
    "--job-dir", type=str, default="./mnist_training", help="Output directory for model and training stats.")
parser.add_argument("--learning-rate", type=float, default=0.002, help="Adam learning rate.")
parser.add_argument(
    '--train-steps', type=int, default=5000,
    help='Training steps.')
parser.add_argument(
    '--batch-size', type=int, default=128,
    help='Batch size to be used.')


def build_estimator(config, params):
    """Build the estimator based on the given config and params
    
    [description]
    
    Args:
        config: [description]
        params: [description]
    """
    return tf.estimator.Estimator(
        model_fn=model_fn,
        config=config,
        params=params)


def architecture(inputs, mode, scope='MnistConvNet'):
    """Return the output operation following the network architecture.
    Args:
        inputs (Tensor): Input Tensor
        mode (ModeKeys): Runtime mode (train, eval, predict)
        scope (str): Name of the scope of the architecture
    Returns:
         Logits output Op for the network.
    """
    with tf.variable_scope(scope):
        inputs = inputs / 255
        input_layer = tf.reshape(inputs, [-1, 28, 28, 1])
        conv1 = tf.layers.conv2d(
            inputs=input_layer,
            filters=20,
            kernel_size=[5, 5],
            padding='valid',
            activation=tf.nn.relu)
        pool1 = tf.layers.max_pooling2d(inputs=conv1, pool_size=[2, 2], strides=2)
        conv2 = tf.layers.conv2d(
            inputs=pool1,
            filters=40,
            kernel_size=[5, 5],
            padding='valid',
            activation=tf.nn.relu)
        pool2 = tf.layers.max_pooling2d(inputs=conv2, pool_size=[2, 2], strides=2)
        flatten = tf.reshape(pool2, [-1, 4 * 4 * 40])
        dense1 = tf.layers.dense(inputs=flatten, units=256, activation=tf.nn.relu)
        dropout = tf.layers.dropout(
            inputs=dense1, rate=0.5, training=mode==tf.estimator.ModeKeys.TRAIN)
        dense2 = tf.layers.dense(inputs=dropout, units=10)
        return dense2


def model_fn(features, labels, mode):
    logits = architecture(features, mode)
    class_predictions = tf.argmax(logits, axis=-1)
    predictions = None
    if mode == PREDICT:
        predictions = {
            "classes": class_predictions,
            "probabilities": tf.nn.softmax(logits=logits, name="softmax_tensor")
        }
    loss = None
    train_op = None
    eval_metric_ops = {}
    # Loss will only be tracked during training or evaluation
    if mode in (TRAIN, EVAL):
        loss = tf.losses.sparse_softmax_cross_entropy(
            labels=tf.cast(labels, tf.int32),
            logits=logits
        )

    if mode == TRAIN:
        train_op = get_train_op_fn(loss, params)

    if mode == EVAL:
        eval_metric_ops = {
            "accuracy": tf.metrics.accuracy(
                labels=labels,
                predictions=class_predictions,
                name="accuracy"
            )
        }

    return tf.estimator.EstimatorSpec(mode=mode, predictions=predictions, loss=loss, eval_metric_ops=eval_metric_ops)




classifier = tf.estimator.Estimator(model_fn=model_fn, model_dir="./py/")

classifier.train(input_fn=train_input_fn)

eval_res = classifier.evaluate(input_fn=eval_input_fn)

def get_train_op_fn(loss, params):
    """Get the training Op.
    Args:
         loss (Tensor): Scalar Tensor that represents the loss function.
         params (object): Hyper-parameters (needs to have `learning_rate`)
    Returns:
        Training Op
    """
    optimizer = tf.train.AdamOptimizer(params.learning_rate)
    train_op = optimizer.minimize(
        loss=loss,
        global_step=tf.train.get_global_step())
    return train_op


def get_train_inputs(batch_size, mnist_data):
    """Return the input function to get the training data.
    Args:
        batch_size (int): Batch size of training iterator that is returned
                          by the input function.
        mnist_data ((array, array): Mnist training data as (inputs, labels).
    Returns:
        DataSet: A tensorflow DataSet object to represent the training input
                 pipeline.
    """
    dataset = tf.data.Dataset.from_tensor_slices(mnist_data)
    dataset = dataset.shuffle(
        buffer_size=1000, reshuffle_each_iteration=True
    ).repeat(count=None).batch(batch_size)
    return dataset


def get_eval_inputs(batch_size, mnist_data):
    """Return the input function to get the validation data.
    Args:
        batch_size (int): Batch size of validation iterator that is returned
                          by the input function.
        mnist_data ((array, array): Mnist test data as (inputs, labels).
    Returns:
        DataSet: A tensorflow DataSet object to represent the validation input
                 pipeline.
    """
    dataset = tf.data.Dataset.from_tensor_slices(mnist_data)
    dataset = dataset.batch(batch_size)
    return dataset


def main(argv=None):
    """Run the training experiment."""
    # Read parameters and input data
    params = parser.parse_args(argv[1:])
    mnist_train, mnist_test = tf.keras.datasets.mnist.load_data()
    config = tf.estimator.RunConfig(
        model_dir=params.job_dir,
        save_summary_steps=100,
        log_step_count_steps=100,
        save_checkpoints_steps=500,
    )
    # Setup the Estimator
    model_estimator = build_estimator(config, params)
    # Setup and start training and validation
    train_spec = tf.estimator.TrainSpec(
        input_fn=lambda: get_train_inputs(params.batch_size, mnist_train),
        max_steps=params.train_steps)
    eval_spec = tf.estimator.EvalSpec(
        input_fn=lambda: get_eval_inputs(params.batch_size, mnist_test),
        steps=None,
        start_delay_secs=10,  # Start evaluating after 10 sec.
        throttle_secs=30  # Evaluate only every 30 sec
    )
    tf.estimator.train_and_evaluate(model_estimator, train_spec, eval_spec)


if __name__ == "__main__":
    # Show debugging output
    tf.logging.set_verbosity(tf.logging.DEBUG)
    tf.app.run()