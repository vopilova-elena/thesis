from deeppavlov import build_model, configs, models
print(configs['morpho_syntax_parser'])
model = build_model(configs['morpho_syntax_parser']['morpho_ru_syntagrus_bert'])
sentences = ["Я шёл домой по незнакомой улице.", "Девушка пела в церковном хоре о всех уставших в чужом краю."]
for parse in model(sentences):
    print(parse)