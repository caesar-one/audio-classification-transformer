from transformers import BertModel, BertConfig
from transformers import ReformerModel, ReformerConfig, Trainer, TrainingArguments
from audiotransformer.models.conv import MSResNet
from torch import nn
from torch.nn import functional as F


class AudioTransformer(nn.Module):
    def __init__(self, d_model, nhead, dim_feedforward, num_layers, num_classes, dropout=0.1, use_conv_embedding=False):
        super(AudioTransformer, self).__init__()
        self.use_conv_embedding = use_conv_embedding
        self.hidden_size = d_model
        if use_conv_embedding:
            self.conv_embedding = MSResNet(1)
            self.hidden_size = 768

        self.config = BertConfig(
            hidden_size=self.hidden_size,
            num_hidden_layers=num_layers,
            intermediate_size=dim_feedforward,
            num_attention_heads=nhead,
            hidden_dropout_prob=dropout
        )
        self.encoder = BertModel(self.config)
        self.decoder = SimpleLinearClassifier(d_model, num_classes, dropout)

    def forward(self, x):
        if self.use_conv_embedding:
            assert x.shape[-1] == 256
            x = self.conv_embedding(x)
        x = self.encoder.forward(inputs_embeds=x)
        # x = (hidden_states, pooled_output) where pooled means that the token is enforced to assume
        # the whole seq meaning. We are interested in the pooled output
        pooled = x[1]
        out = self.decoder(pooled)
        return out


class LinearClassifier(nn.Module):
    def __init__(self, hidden_size, num_classes):
        super(LinearClassifier, self).__init__()
        self.dense = nn.Linear(hidden_size, hidden_size)
        self.layer_norm = nn.LayerNorm(hidden_size, eps=10e-12)
        self.decoder = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        x = self.dense(x)
        x = F.gelu(x)
        x = self.layer_norm(x)
        x = self.decoder(x)
        return x

class SimpleLinearClassifier(nn.Module):
    def __init__(self, hidden_size, num_classes, dropout=0.1):
        super(SimpleLinearClassifier, self).__init__()
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        x = self.dropout(x)
        x = self.classifier(x)
        return x

class AudioReformer(nn.Module):
    def __init__(self, config, d_model, num_classes, dropout=0.1):
        super(AudioReformer, self).__init__()
        self.config = config
        self.encoder = ReformerModel(self.config)
        self.decoder = SimpleLinearClassifier(int(d_model * 2), num_classes, dropout)

    def forward(self, x):
        x = self.encoder.forward(inputs_embeds=x)
        # x = (hidden_states,) <-- tuple
        # pooled means that the token is enforced to assume the whole seq meaning.
        # We are interested in first hidden state
        x = x[0]
        pooled = x[:,0,:]
        out = self.decoder(pooled)
        return out