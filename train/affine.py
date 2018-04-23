# -*- coding: utf-8 -*-
"""
Created on Sun Nov 12 11:21:21 2017

@author: samsung
"""
import tensorflow as tf
import numpy as np
from text_cnn import TextCNN


class Affine(object):
# Combine all the pooled features
    def __init__(
      self, sequence_length_head, sequence_length_body, num_classes, vocab_size_head, vocab_size_body,
      embedding_size, filter_sizes, num_filters, l2_reg_lambda=0.1):
        
        self.input_y = tf.placeholder(tf.float32, [None, num_classes], name="input_y")
        self.dropout_keep_prob = tf.placeholder(tf.float32, name="dropout_keep_prob")
        self.input_x_head = tf.placeholder(tf.int32, [None, sequence_length_head], name="input_x_head")
        self.input_x_body = tf.placeholder(tf.int32, [None, sequence_length_body], name="input_x_body")
        
        # Embedding layer
        self.embeddings_head = tf.Variable(
                tf.random_uniform([vocab_size_head, embedding_size], -1.0, 1.0),trainable=False)#trainable=false
        self.embedded_chars_head = tf.nn.embedding_lookup(self.embeddings_head, self.input_x_head)
        self.embedded_chars_expanded_head = tf.expand_dims(self.embedded_chars_head, -1)

        self.embeddings_body = tf.Variable(
                tf.random_uniform([vocab_size_body, embedding_size], -1.0, 1.0),trainable=False)#trainable=false
        self.embedded_chars_body = tf.nn.embedding_lookup(self.embeddings_body, self.input_x_body)
        self.embedded_chars_expanded_body = tf.expand_dims(self.embedded_chars_body, -1)
        
        # Create a convolution + maxpool layer for each filter size
        self.pooled_outputs_head = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.name_scope("conv-maxpool-head-%s" % filter_size):
                # Convolution Layer
                filter_shape = [filter_size, embedding_size, 1, 256]
                W_head = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W_head")
                b_head = tf.Variable(tf.constant(0.1, shape=[256]), name="b_head")
                conv_head = tf.nn.conv2d(
                    self.embedded_chars_expanded_head,
                    W_head,
                    strides=[1, 1, 1, 1],
                    padding="VALID",
                    name="conv")
                # Apply nonlinearity
                h_head = tf.nn.relu(tf.nn.bias_add(conv_head, b_head), name="relu_head")
                # Maxpooling over the outputs
                pooled_head = tf.nn.max_pool(
                    h_head,
                    ksize=[1, sequence_length_head - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="pool")
                self.pooled_outputs_head.append(pooled_head)

        self.pooled_outputs_body = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.name_scope("conv-maxpool-body-%s" % filter_size):
                # Convolution Layer
                filter_shape = [filter_size, embedding_size, 1, 1024]
                W_body = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W_body")
                b_body = tf.Variable(tf.constant(0.1, shape=[1024]), name="b_body")
                conv_body = tf.nn.conv2d(
                    self.embedded_chars_expanded_body,
                    W_body,
                    strides=[1, 1, 1, 1],
                    padding="VALID",
                    name="conv")
                # Apply nonlinearity
                h_body = tf.nn.relu(tf.nn.bias_add(conv_body, b_body), name="relu_body")
                # Maxpooling over the outputs
                pooled_body = tf.nn.max_pool(
                    h_body,
                    ksize=[1, sequence_length_body - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="pool")
                self.pooled_outputs_body.append(pooled_body)        
        
        l2_loss = tf.constant(0.0)
        
        pooled_outputs = tf.concat([self.pooled_outputs_head,self.pooled_outputs_body],-1,name='preconcat')
        print(pooled_outputs.shape)
        num_filters_total = num_filters * len(filter_sizes)
        self.h_pool = tf.concat(pooled_outputs, 3, name='concat')
        self.h_pool_flat = tf.reshape(self.h_pool, [-1, num_filters_total])
        print("여기")
        print(self.h_pool_flat.shape)
	
        W_fc1 = tf.Variable(tf.truncated_normal([1280,1024],stddev=0.1),name="W_fc1")
        b_fc1 = tf.Variable(tf.constant(0.1,shape=[1024]),name="b_fc1")
        h_fc1 = tf.nn.relu(tf.matmul(self.h_pool_flat,W_fc1) + b_fc1)
        print(h_fc1.shape)
        print("22222")
      
        # Add dropout
        with tf.name_scope("dropout"):
            self.h_drop = tf.nn.dropout(h_fc1, self.dropout_keep_prob)

        # Final (unnormalized) scores and predictions
        with tf.name_scope("output"):
            W = tf.get_variable(
                "W",
                shape=[1024, num_classes],
                initializer=tf.contrib.layers.xavier_initializer())
            b = tf.Variable(tf.constant(0.1, shape=[num_classes]), name="b")
            l2_loss += tf.nn.l2_loss(W)
            l2_loss += tf.nn.l2_loss(b)
            self.scores = tf.nn.xw_plus_b(self.h_drop, W, b, name="scores")
            self.predictions = tf.argmax(self.scores, 1, name="predictions")

        # CalculateMean cross-entropy loss
        with tf.name_scope("loss"):
            print(self.scores.shape)
            losses = tf.nn.softmax_cross_entropy_with_logits(logits = self.scores, labels = self.input_y)
            self.loss = tf.reduce_mean(losses) + l2_reg_lambda * l2_loss

        # Accuracy
        with tf.name_scope("accuracy"):
            print("%d/%d",self.predictions,self.input_y)
            correct_predictions = tf.equal(self.predictions, tf.argmax(self.input_y, 1))
            self.accuracy = tf.reduce_mean(tf.cast(correct_predictions, "float"), name="accuracy")
