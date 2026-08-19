


## API structure 


models
    specfic models ( one class per model)


services
    workers
    helpers
    reconsilliation
    vacation_service
    flight_service
    and others associatged with the models


repos
    each model has its own dedicated repo that is specific to the respective model
    to avoid diffs, contamination of logic but also to separate concerns and practices good code hygeine


services are for interacting with the application, performing ORM quries, we do not want raw queries for any application but windows would be acceptable upon justfication and approval that should eb flagged to the operatorFlight