import pandas as pd
import numpy as np
import pickle
import torch
from pytorch_pretrained_bert import BertTokenizer, BertModel, BertForMaskedLM
from scipy.spatial.distance import cosine
from scipy.spatial.distance import cdist

# OPTIONAL: if you want to have more information on what's happening, activate the logger as follows
import logging
logging.basicConfig(level=logging.INFO)

class Bert_embedder:
    def __init__(self, data: pd.DataFrame, model: object):
        self.data = data
        self.model = model
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    def get_bert_dict(self):
        bert_dict = {}
        lookup_tokens = []
        lookup_embeddings = []
        for i in self.data.columns:
            bert_dict[i] = {}
            self.data[i].dropna(inplace = True)
            for j in range(len(self.data[i])):
                bert_dict[i][j] = {}
                bert_dict[i][j]["text"] = self.data[i][j]
                one = mark_and_tokenize(str(self.data[i][j]), self.tokenizer)
                bert_dict[i][j]["tokens"] = one
                # we only want to add the words to the look up table, not the CLS and the SEP markers
                words_only = one[1:-1]
                for word in words_only:
                    lookup_tokens.append(word)
                two = convert_to_ids(one, self.tokenizer)
                three = segments(two)
                token_tensor, segment_tensors = convert_to_torch(two, three)
                embeddings = get_hidden_states(token_tensor, segment_tensors, self.model)
                embeddings_l1 = layer_1_embeddings(embeddings)
                for tensor in embeddings_l1[1:-1]:
                    lookup_embeddings.append(tensor.numpy())
                bert_dict[i][j]["emb_l1"] = embeddings_l1
                #embeddings_cat = concatenate(embeddings)
                #bert_dict[i][j]["emb_cat"] = embeddings_cat
                # we add the embeddings to the look up table, but not the ones from CLS and SEP
                #for tensor in embeddings_cat[1:-1]:
                 #   lookup_embeddings.append(tensor.numpy())
                #embeddings_sum = summing(embeddings)
                #bert_dict[i][j]["emb_sum"] = embeddings_sum
                sentence_embeddings = sentence_encoding(embeddings)
                bert_dict[i][j]["emb_sen"] = sentence_embeddings
            return bert_dict, lookup_tokens, lookup_embeddings

def mark_and_tokenize(comment, tokenizer):
    marked = "[CLS] " + comment + " [SEP]"
    ergebnis = tokenizer.tokenize(marked)
    return ergebnis

def convert_to_ids(comment, tokenizer):
    # Map the token strings to their vocabulary indeces.
    indexed_tokens = tokenizer.convert_tokens_to_ids(comment)
    return indexed_tokens

def segments(comment):
    # Mark each of the tokens as belonging to sentence "1".
    segments_ids = [1] * len(comment)
    return segments_ids

def convert_to_torch(comment, segments):
    # Convert inputs to PyTorch tensors
    tokens_tensor = torch.tensor([comment])
    segments_tensors = torch.tensor([segments])
    return tokens_tensor, segments_tensors


def get_hidden_states(token_tensor, segment_tensors, model):
    # Predict hidden states features for each layer
    with torch.no_grad():
        encoded_layers, _ = model(token_tensor, segment_tensors)
        # print(encoded_layers)
    # Concatenate the tensors for all layers. We use `stack` here to
    # create a new dimension in the tensor.
    token_embeddings = torch.stack(encoded_layers, dim=0)

    # Remove dimension 1, the "batches".
    token_embeddings = torch.squeeze(token_embeddings, dim=1)

    # Swap dimensions 0 and 1.
    token_embeddings = token_embeddings.permute(1, 0, 2)

    return token_embeddings

def concatenate(embeddings):
    # Stores the token vectors, with shape [22 x 3,072]
    token_vecs_cat = []

    # `token_embeddings` is a [22 x 12 x 768] tensor.

    # For each token in the sentence...
    for token in embeddings:

        # `token` is a [12 x 768] tensor

        # Concatenate the vectors (that is, append them together) from the last
        # four layers.
        # Each layer vector is 768 values, so `cat_vec` is length 3,072.
        cat_vec = torch.cat((token[-1], token[-2], token[-3], token[-4]), dim=0)

        # Use `cat_vec` to represent `token`.
        token_vecs_cat.append(cat_vec)
    return token_vecs_cat

def summing(embeddings):
    # Stores the token vectors, with shape [22 x 768]
    token_vecs_sum = []

    # `token_embeddings` is a [22 x 12 x 768] tensor.

    # For each token in the sentence...
    for token in embeddings:

        # `token` is a [12 x 768] tensor

        # Sum the vectors from the last four layers.
        sum_vec = torch.sum(token[-4:], dim=0)

        # Use `sum_vec` to represent `token`.
        token_vecs_sum.append(sum_vec)
    return token_vecs_sum

def layer_1_embeddings(embeddings):
    token_vecs = embeddings[:,0]
    return token_vecs

def sentence_encoding(embeddings):
    # embeddings has shape [53 x 12 x 768]

    # `token_vecs` is a tensor with shape [53 x 768]
    token_vecs = embeddings[:, 0]
    #print(token_vecs.shape())

    # Calculate the average of all 53 token vectors.
    sentence_embedding = torch.mean(token_vecs, dim=0)
    return sentence_embedding
