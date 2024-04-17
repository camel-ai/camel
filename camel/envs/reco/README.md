# Movie Recommendation Environment

We now only use `omdb` API, which is used to retrieve movie information.
The environment is under `movie_rec.py`.

In order to use this environment, please follow the instruction here to register and get your own user key:

https://www.omdbapi.com/apikey.aspx

Then, you can set the environment variable `OMDB_API_KEY` to your key:
```bash
export OMDB_API_KEY=your_key
```

## User Request Logic

There are four attributes that a user can specify:
> Type: Movie or TV show 
> 
> Year: The year of release 80s, 90s, 2000s, "recent" (after 2010)
> 
> Genre: a movie/tv show can have multiple genres, we only
> 
> Age-Restriction: 'child-friendly'/'family-friendly' or 'R-rated'

The user can specify the attributes in the following way:

1. Choose a type: movie or tv show
2. Choose 0, 1, or 2 year ranges. Examples: "80s or 90s", "2000s", "80s or recent".
3. Choose 0, 1, or 2 genres. Examples: "action", "comedy", or "action and comedy".
4. Choose 0 or 1 age-restriction: Examples: "None", "adult-only", or  'child-friendly'.
   However, if the genre is any of 'Crime', 'War', 'Romance', then we remove age-restriction if it's 'child-friendly'.
   If the genre is any of 'History', 'Biography', 'Documentary', 'Sport', 'Musical', then we remove age-restriction if it's 'R-rated'.


Some example queries look like:

> Looking for some iconic Musical or Adventure TV shows. Any pointers?
> 
> Can you recommend some Sci-Fi movies from the 80s or past few years? Please point me in the right direction.

## Item Verification Logic

For each item, we check the following five attributes:

1. **Existence**: whether the item exists in the IMDB database.
2. **Type**: each item needs to match the type (movie or TV show) specified by the user.
3. **Year**: each item needs to match the year range specified by the user. If multiple year ranges are specified, then the item only needs to match one of them.
4. **Genre**: each item can have multiple genres -- these genres need to be a superset of user specified genres. 
   - For example, if a movie is labeled as `Action` and `Comedy`, and the user preference genre is `Comedy`, this will be a match.
   - For example, if a movie is labeled as `Action` and `Comedy`, and the user preference genre is `Comedy` and `War`, this will not be a match.
   - You can explore some combinations of genres here: https://www.imdb.com/search/title/
5. **Age-Restriction**: each item needs to match the age-restriction specified by the user.

## Instruction Type

`b`: Partial user preference is given -- some preference is hidden from the agent during the initial request.

`c`: Full user preference is given.

## Feedback Logic

For `fp`, `fn`, the simulated user will give some suggestions of itmes that satisfy constraint, but not joint constraint -- only single constraint.
This means for attribute genre `Action`, the user will give some `Action` movies as examples, but will not 
make sure these items also conform to other preferences such as `year`.