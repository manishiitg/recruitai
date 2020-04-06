#### Multi Account ####

What this means. 

We will have multiple frontend deployed for different customers.

The ai system i.e search, redis, mongodb, all should be difficult for every customer.

Also different customer might have different payment plans so priority of processing can also be different. 

Need to manage this.....

things to consider

a) google cloud storage for images should be different for every customer
b) mongodb will be different for every customer. both ip and db. so need fetch this information some how
c) redis will be different for every customer
d) elastic search index


For now, i.e initally we will handle this manually.
And for every account there will be yml config or json config file



e) need to look at logs management per account as well