# -*- coding: utf-8 -*-
# @Author: Yue Peng
# @Email: yuepaang@gmail.com
# @Date: Nov 05, 2018
# @Created on: 21:43:39
# @Description: Embedding Dropout
import torch
import numpy as np


def embedded_dropout(embed, words, dropout=0.1, scale=None):
    if dropout:
        # (E * V)
        mask = embed.weight.data.new().resize_((embed.weight.size(0), 1)).bernoulli_(1 - dropout).expand_as(embed.weight) / (1 - dropout)
        masked_embed_weight = mask * embed.weight
    else:
        masked_embed_weight = embed.weight

    if scale:
        masked_embed_weight = scale.expand_as(masked_embed_weight) * masked_embed_weight
    
    padding_idx = embed.padding_idx
    if padding_idx is None:
        padding_idx = -1
    X = torch.nn.functional.embedding(words, masked_embed_weight, padding_idx, embed.max_norm, embed.norm_type, embed.scale_grad_by_freq, embed.sparse)

    return X


def main():
    V = 50
    h = 4
    bptt = 10
    batchSz = 2

    embed = torch.nn.Embedding(V, h)

    words = np.random.random_integers(low=0, high=V-1, size=(batchSz, bptt))
    words = torch.LongTensor(words)

    origX = embed(words)
    X = embedded_dropout(embed, words)

    print(origX)
    print(X)

if __name__ == '__main__':
    main()
