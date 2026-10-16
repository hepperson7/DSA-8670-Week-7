# DSA 8670 Week 7 

Analysis Question: "How do square footage, # of bedrooms, and # of bathrooms affect selling price and does this differ across neighborhoods?"

Two models were created: a common-slope OLS model and an interaction model. The common model evaluated square footage, # of bedrooms, and # of bathrooms for all neighborhoods. There was a p-value of <0.001 for each factor, indicating that these are signficant factors. The R squared value for this model qas 0.7686. The interaction model seemed to perform better, as its R-squared value was 0.8331. All features had a p-value of <0.001, indicating significance. 

In both models, adding square footage and bathrooms was predicted to increase the SalePrice, but adding a bedroom was predicted to decrease selling price. I found the bedroom result to be particularly odd. On the surface, it seems illogical that adding a bedroom would decrease the value of a house. However, as codex pointed out, there are other features that determine selling price such as age and condition. Therefore, you can't make the claim that just adding a bedroom will decreate the value of the home. 