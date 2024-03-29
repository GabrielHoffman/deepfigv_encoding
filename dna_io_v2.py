#!/usr/bin/env python
from __future__ import print_function
import sys
from collections import OrderedDict

import numpy as np
import numpy.random as npr
from sklearn import preprocessing
import gzip
import pdb

################################################################################
# dna_io.py
#
# Methods to load the training data.
################################################################################

################################################################################
# align_seqs_scores
#
# Align entries from input dicts into numpy matrices ready for analysis.
#
# Input
#  seq_vecs:      Dict mapping headers to sequence vectors.
#  seq_scores:    Dict mapping headers to score vectors.
#
# Output
#  train_seqs:    Matrix with sequence vector rows.
#  train_scores:  Matrix with score vector rows.
################################################################################
def align_seqs_scores_1hot(seq_vecs, seq_scores, seq_annot, sort=True):
    if sort:
        seq_headers = sorted(seq_vecs.keys())
    else:
        seq_headers = seq_vecs.keys()

    # construct lists of vectors
    train_scores = []
    train_seqs = []
    train_annot = []
    for header in seq_headers:
        train_seqs.append(seq_vecs[header])
        train_scores.append(seq_scores[header])
        train_annot.append(seq_annot[header])

    # stack into matrices
    train_seqs = np.vstack(train_seqs)
    train_scores = np.vstack(train_scores)
    train_annot = np.vstack(train_annot)

    return train_seqs, train_scores, train_annot


################################################################################
# check_order
#
# Check that the order of sequences in a matrix of vectors matches the order
# in the given fasta file
################################################################################
def check_order(seq_vecs, fasta_file):
    # reshape into seq x 4 x len
    seq_mats = np.reshape(seq_vecs, (seq_vecs.shape[0], 4, seq_vecs.shape[1]/4))

    # generate sequences
    real_seqs = []
    for i in range(seq_mats.shape[0]):
        seq_list = ['']*seq_mats.shape[2]
        for j in range(seq_mats.shape[2]):
            if seq_mats[i,0,j] == 1:
                seq_list[j] = 'A'
            elif seq_mats[i,1,j] == 1:
                seq_list[j] = 'C'
            elif seq_mats[i,2,j] == 1:
                seq_list[j] = 'G'
            elif seq_mats[i,3,j] == 1:
                seq_list[j] = 'T'

            # GEH 11/10/17
            # ambiguity codes
            # A C G T
            # 0 1 2 3 
            elif (seq_mats[i,0,j] == 0.5) and seq_mats[i,1,j] == 0.5:
                seq_list[j] = 'M'
            elif (seq_mats[i,0,j] == 0.5) and seq_mats[i,2,j] == 0.5:
                seq_list[j] = 'W'
            elif (seq_mats[i,0,j] == 0.5) and seq_mats[i,3,j] == 0.5:
                seq_list[j] = 'T'
            elif (seq_mats[i,1,j] == 0.5) and seq_mats[i,2,j] == 0.5:
                seq_list[j] = 'S'
            elif (seq_mats[i,1,j] == 0.5) and seq_mats[i,3,j] == 0.5:
                seq_list[j] = 'Y'
            elif (seq_mats[i,2,j] == 0.5) and seq_mats[i,3,j] == 0.5:
                seq_list[j] = 'K'

            else:
                seq_list[j] = 'N'
        real_seqs.append(''.join(seq_list))

    # load FASTA sequences
    fasta_seqs = []
    for line in gzip.open(fasta_file):
        if line[0] == '>':
            fasta_seqs.append('')
        else:
            fasta_seqs[-1] += line.rstrip()

    # check
    assert(len(real_seqs) == len(fasta_seqs))

    for i in range(len(fasta_seqs)):
        try:
            assert(fasta_seqs[i] == real_seqs[i])
        except:
            print(fasta_seqs[i])
            print(real_seqs[i])
            exit()


################################################################################
# dna_one_hot
#
# Input
#  seq:
#
# Output
#  seq_vec: Flattened column vector
################################################################################
'''
def dna_one_hot(seq, seq_len=None):
    if seq_len == None:
        seq_len = len(seq)

    seq = seq.replace('A','0')
    seq = seq.replace('C','1')
    seq = seq.replace('G','2')
    seq = seq.replace('T','3')

    # map nt's to a matrix 4 x len(seq) of 0's and 1's.
    seq_code = np.zeros((4,seq_len), dtype='int8')
    for i in range(seq_len):
        try:
            seq_code[int(seq[i]),i] = 1
        except:
            # print >> sys.stderr, 'Non-ACGT nucleotide encountered'
            seq_code[:,i] = 0.25

    # flatten and make a column vector 1 x len(seq)
    seq_vec = seq_code.flatten()[None,:]

    return seq_vec
'''

def dna_one_hot(seq, seq_len=None, flatten=True):
    if seq_len == None:
        seq_len = len(seq)
        seq_start = 0
    else:
        if seq_len <= len(seq):
            # trim the sequence
            seq_trim = (len(seq)-seq_len) // 2
            seq = seq[seq_trim:seq_trim+seq_len]
            seq_start = 0
        else:
            seq_start = (seq_len-len(seq)) // 2

    seq = seq.upper()

    seq = seq.replace('A','0')
    seq = seq.replace('C','1')
    seq = seq.replace('G','2')
    seq = seq.replace('T','3')

    # map nt's to a matrix 4 x len(seq) of 0's and 1's.
    #  dtype='int8' fails for N's
    seq_code = np.zeros((4,seq_len), dtype='float16')
    for i in range(seq_len):
        if i < seq_start:
            seq_code[:,i] = 0.25
        # GEH 11/10/17
        # ambiguity codes
        # A C G T
        # 0 1 2 3 
        elif seq[i-seq_start] == "M":
            seq_code[0,i] = 0.5
            seq_code[1,i] = 0.5
        elif seq[i-seq_start] == "R":
            seq_code[0,i] = 0.5
            seq_code[2,i] = 0.5
        elif seq[i-seq_start] == "W":
            seq_code[0,i] = 0.5
            seq_code[3,i] = 0.5
        elif seq[i-seq_start] == "S":
            seq_code[1,i] = 0.5
            seq_code[2,i] = 0.5
        elif seq[i-seq_start] == "Y":
            seq_code[1,i] = 0.5
            seq_code[3,i] = 0.5
        elif seq[i-seq_start] == "K":
            seq_code[2,i] = 0.5
            seq_code[3,i] = 0.5
        else:
            try:
                seq_code[int(seq[i-seq_start]),i] = 1
            except:
                seq_code[:,i] = 0.25

    # flatten and make a column vector 1 x len(seq)
    if flatten:
        seq_vec = seq_code.flatten()[None,:]

    return seq_vec




################################################################################
# fasta2dict
#
# Read a multifasta file into a dict.  Taking the whole line as the key.
#
# I've found this can be quite slow for some reason, even for a single fasta
# entry.
################################################################################
def fasta2dict(fasta_file):
    fasta_dict = OrderedDict()
    header = ''

    for line in gzip.open(fasta_file):
        if line[0] == '>':
            #header = line.split()[0][1:]
            header = line[1:].rstrip()
            fasta_dict[header] = ''
        else:
            fasta_dict[header] += line.rstrip()

    return fasta_dict


################################################################################
# hash_scores
#
# Input
#  scores_file:
#
# Output
#  seq_scores:  Dict mapping FASTA headers to score vectors.
################################################################################
def hash_scores(scores_file):
    seq_scores = {}
    seq_annot = {}

    n_lines_processed = 0
    for line in gzip.open(scores_file):
        a = line.split()

        try:
            # seq_scores[a[0]] = np.array([float(a[i]) for i in range(1,len(a))])

            # GEH
            # 11/10/2017
            # parse data in melted format now
            seq_scores[a[0]] = np.array([float(a[2])])
            # seq_scores[a[0]] = np.array([float(a[i]) for i in range(1,1)])
            # seq_annot[a[0]] = np.array([a[1], a[3]])
            seq_annot[a[0]] = np.array([a[1]])

            n_lines_processed = n_lines_processed + 1
            if n_lines_processed % 50000 == 0:
                print(" scores processed:", n_lines_processed, end='\r')
                sys.stdout.flush()

        except:
            if n_lines_processed != 0:
                print('Ignoring header line:', n_lines_processed, file=sys.stderr)

    # consider converting the scores to integers
    int_scores = True
    for header in seq_scores:
        if not np.equal(np.mod(seq_scores[header], 1), 0).all():
            int_scores = False
            break

    if int_scores:
        for header in seq_scores:
            seq_scores[header] = seq_scores[header].astype('int8')

        '''
        for header in seq_scores:
            if seq_scores[header] > 0:
                seq_scores[header] = np.array([0, 1], dtype=np.min_scalar_type(1))
            else:
                seq_scores[header] = np.array([1, 0], dtype=np.min_scalar_type(1))
        '''

    return seq_scores, seq_annot


################################################################################
# hash_sequences_1hot
#
# Input
#  fasta_file:  Input FASTA file.
#  extend_len:  Extend the sequences to this length.
#
# Output
#  seq_vecs:    Dict mapping FASTA headers to sequence representation vectors.
################################################################################
def hash_sequences_1hot(fasta_file, extend_len=None):
    # determine longest sequence
    if extend_len is not None:
        seq_len = extend_len
    else:
        seq_len = 0
        seq = ''
        n_lines_processed = 0
        for line in gzip.open(fasta_file):
           
            if line[0] == '>':
                if seq:
                    seq_len = max(seq_len, len(seq))

                header = line[1:].rstrip()
                seq = ''
                # GEH 
                # 11/10/2017
                # add progress
                n_lines_processed = n_lines_processed +1
                if n_lines_processed % 50000 == 0:
                    print(" fasta seq processed:", n_lines_processed, end='\r')
                    sys.stdout.flush()
            else:
                seq += line.rstrip()
        print(" fasta seq processed:", n_lines_processed, end='\n')       

        if seq:
            seq_len = max(seq_len, len(seq))

    # load and code sequences
    seq_vecs = OrderedDict()
    seq = ''
    n_lines_processed2 = 0
    for line in gzip.open(fasta_file):
        if line[0] == '>':
            # GEH 
            # 11/10/2017
            # add progress
            n_lines_processed2 = n_lines_processed2 +1
            if n_lines_processed2 % 5000 == 0:
                v = round( n_lines_processed2 / (n_lines_processed/100.0),2 )
                print(" fasta seq recoded: ", v, "%       ", end='\r')
                sys.stdout.flush()
            if seq:
                seq_vecs[header] = dna_one_hot(seq, seq_len)

            header = line[1:].rstrip()
            seq = ''
        else:
            seq += line.rstrip()
    print(" fasta seq recoded: 100%       ", end='\n')
    if seq:
        seq_vecs[header] = dna_one_hot(seq, seq_len)

    return seq_vecs


################################################################################
# load_data_1hot
#
# Input
#  fasta_file:  Input FASTA file.
#  scores_file: Input scores file.
#
# Output
#  train_seqs:    Matrix with sequence vector rows.
#  train_scores:  Matrix with score vector rows.
################################################################################
def load_data_1hot(fasta_file, scores_file, extend_len=None, mean_norm=True, whiten=False, permute=True, sort=False):
   
    # load sequences
    seq_vecs = hash_sequences_1hot(fasta_file, extend_len)

    # load scores
    seq_scores, seq_annot = hash_scores(scores_file)

    # align and construct input matrix
    train_seqs, train_scores, train_annot = align_seqs_scores_1hot(seq_vecs, seq_scores, seq_annot, sort)

    # whiten scores
    if whiten:
        train_scores = preprocessing.scale(train_scores)
    elif mean_norm:
        train_scores -= np.mean(train_scores, axis=0)

    # randomly permute
    if permute:
        order = npr.permutation(train_seqs.shape[0])
        train_seqs = train_seqs[order]
        train_scores = train_scores[order]
        train_annot = train_annot[order]

    return train_seqs, train_scores, train_annot


################################################################################
# load_sequences
#
# Input
#  fasta_file:  Input FASTA file.
#
# Output
#  train_seqs:    Matrix with sequence vector rows.
#  train_scores:  Matrix with score vector rows.
################################################################################
def load_sequences(fasta_file, permute=False):
    # load sequences
    seq_vecs = hash_sequences_1hot(fasta_file)

    # stack
    train_seqs = np.vstack(seq_vecs.values())

    # randomly permute the data
    if permute:
        order = npr.permutation(train_seqs.shape[0])
        train_seqs = train_seqs[order]

    return train_seqs


################################################################################
# one_hot_get
#
# Input
#  seq_vec:
#  pos:
#
# Output
#  nt
################################################################################
def one_hot_get(seq_vec, pos):
    seq_len = len(seq_vec)/4

    a0 = 0
    c0 = seq_len
    g0 = 2*seq_len
    t0 = 3*seq_len

    if seq_vec[a0+pos] == 1:
        nt = 'A'
    elif seq_vec[c0+pos] == 1:
        nt = 'C'
    elif seq_vec[g0+pos] == 1:
        nt = 'G'
    elif seq_vec[t0+pos] == 1:
        nt = 'T'
    # GEH 11/10/17
    # ambiguity codes
    # A C G T
    # 0 1 2 3 
    elif (seq_vec[a0+pos] == 0.5) and (seq_vec[c0+pos] == 0.5):
        nt = 'M'
    elif (seq_vec[a0+pos] == 0.5) and (seq_vec[g0+pos] == 0.5):
        nt = 'R'
    elif (seq_vec[a0+pos] == 0.5) and (seq_vec[t0+pos] == 0.5):
        nt = 'W'
    elif (seq_vec[c0+pos] == 0.5) and (seq_vec[g0+pos] == 0.5):
        nt = 'S'
    elif (seq_vec[c0+pos] == 0.5) and (seq_vec[t0+pos] == 0.5):
        nt = 'Y'
    elif (seq_vec[g0+pos] == 0.5) and (seq_vec[t0+pos] == 0.5):
        nt = 'K'

    else:
        nt = 'N'

    return nt


################################################################################
# one_hot_set
#
# Assuming the sequence is given as 4x1xLENGTH
# Input
#  seq_vec:
#  pos:
#  nt
#
# Output
################################################################################
def one_hot_set(seq_vec, pos, nt):
    # zero all
    for ni in range(4):
        seq_vec[ni,0,pos] = 0

    # set the nt
    if nt == 'A':
        seq_vec[0,0,pos] = 1
    elif nt == 'C':
        seq_vec[1,0,pos] = 1
    elif nt == 'G':
        seq_vec[2,0,pos] = 1
    elif nt == 'T':
        seq_vec[3,0,pos] = 1

    # GEH 11/10/17
    # ambiguity codes
    # A C G T
    # 0 1 2 3 

    elif nt == 'M':
        seq_vec[0,0,pos] = 0.5
        seq_vec[1,0,pos] = 0.5

    elif nt == 'R':
        seq_vec[0,0,pos] = 0.5
        seq_vec[2,0,pos] = 0.5

    elif nt == 'W':
        seq_vec[0,0,pos] = 0.5
        seq_vec[3,0,pos] = 0.5

    elif nt == 'S':
        seq_vec[1,0,pos] = 0.5
        seq_vec[2,0,pos] = 0.5

    elif nt == 'Y':
        seq_vec[1,0,pos] = 0.5
        seq_vec[3,0,pos] = 0.5

    elif nt == 'K':
        seq_vec[2,0,pos] = 0.5
        seq_vec[3,0,pos] = 0.5

    else:
        for ni in range(4):
            seq_vec[ni,0,pos] = 0.25




################################################################################
# one_hot_set_1d
#
# Input
#  seq_vec:
#  pos:
#  nt
#
# Output
################################################################################
def one_hot_set_1d(seq_vec, pos, nt):
    seq_len = len(seq_vec)/4

    a0 = 0
    c0 = seq_len
    g0 = 2*seq_len
    t0 = 3*seq_len

    # zero all
    seq_vec[a0+pos] = 0
    seq_vec[c0+pos] = 0
    seq_vec[g0+pos] = 0
    seq_vec[t0+pos] = 0

    # set the nt
    if nt == 'A':
        seq_vec[a0+pos] = 1
    elif nt == 'C':
        seq_vec[c0+pos] = 1
    elif nt == 'G':
        seq_vec[g0+pos] = 1
    elif nt == 'T':
        seq_vec[t0+pos] = 1

    # GEH 11/10/17
    # ambiguity codes
    # A C G T
    # 0 1 2 3 

    elif nt == 'M':
        seq_vec[a0+pos] = 0.5
        seq_vec[c0+pos] = 0.5

    elif nt == 'R':
        seq_vec[a0+pos] = 0.5
        seq_vec[g0+pos] = 0.5

    elif nt == 'W':
        seq_vec[a0+pos] = 0.5
        seq_vec[t0+pos] = 0.5

    elif nt == 'S':
        seq_vec[c0+pos] = 0.5
        seq_vec[g0+pos] = 0.5

    elif nt == 'Y':
        seq_vec[c0+pos] = 0.5
        seq_vec[t0+pos] = 0.5

    elif nt == 'K':
        seq_vec[g0+pos] = 0.5
        seq_vec[t0+pos] = 0.5

    else:
        seq_vec[a0+pos] = 0.25
        seq_vec[c0+pos] = 0.25
        seq_vec[g0+pos] = 0.25
        seq_vec[t0+pos] = 0.25





def vecs2dna(seq_vecs):
    ''' vecs2dna

    Input:
        seq_vecs:
    Output:
        seqs
    '''

    # possibly reshape
    if len(seq_vecs.shape) == 2:
        seq_vecs = np.reshape(seq_vecs, (seq_vecs.shape[0], 4, -1))
    elif len(seq_vecs.shape) == 4:
        seq_vecs = np.reshape(seq_vecs, (seq_vecs.shape[0], 4, -1))

    seqs = []
    for i in range(seq_vecs.shape[0]):
        seq_list = ['']*seq_vecs.shape[2]
        for j in range(seq_vecs.shape[2]):
            if seq_vecs[i,0,j] == 1:
                seq_list[j] = 'A'
            elif seq_vecs[i,1,j] == 1:
                seq_list[j] = 'C'
            elif seq_vecs[i,2,j] == 1:
                seq_list[j] = 'G'
            elif seq_vecs[i,3,j] == 1:
                seq_list[j] = 'T'

            # GEH 11/10/17
            # ambiguity codes
            # A C G T
            # 0 1 2 3 
            elif (seq_vecs[i,0,j] == 0.5) and (seq_vecs[i,1,j] == 0.5):
                # M = A / C                  
                seq_list[j] = 'M'
            elif (seq_vecs[i,0,j] == 0.5) and (seq_vecs[i,2,j] == 0.5):
                # R = A / G                  
                seq_list[j] = 'R'
            elif (seq_vecs[i,0,j] == 0.5) and (seq_vecs[i,3,j] == 0.5): 
                # W = A / T                
                seq_list[j] = 'W'
            elif (seq_vecs[i,1,j] == 0.5) and (seq_vecs[i,2,j] == 0.5): 
                # S = C / G                 
                seq_list[j] = 'S'
            elif (seq_vecs[i,1,j] == 0.5) and (seq_vecs[i,3,j] == 0.5): 
                # Y = C / T              
                seq_list[j] = 'Y'
            elif (seq_vecs[i,2,j] == 0.5) and (seq_vecs[i,3,j] == 0.5): 
                # K = G / T         
                seq_list[j] = 'K'

            elif seq_vecs[i,:,j].sum() == 1:
                seq_list[j] = 'N'
            else:
                print('Malformed position vector: ', seq_vecs[i,:,j], 'for sequence %d position %d' % (i,j), file=sys.stderr)
        seqs.append(''.join(seq_list))
    return seqs

# IUPAC Ambiguity Codes
# There are cdoes for 3 nucleotides, but let's igmore those 
# M = A / C
# R = A / G
# W = A / T
# S = C / G
# Y = C / T
# K = G / T
