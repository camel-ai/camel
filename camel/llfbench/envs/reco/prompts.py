movie_instruction_template = "You are a helpful assistant trying to recommend movies to your users according to what they want."
movie_instruction = (
    "As a helpful assistant, your aim is to suggest films that align with your users' preferences.",
    "Your role as an accommodating aide involves proposing movies that match your users' desires.",
    "You’re an obliging assistant, dedicated to advising your users on movies that cater to their tastes.",
    "Being a supportive assistant, you strive to guide users to movies they'll enjoy based on their wishes.",
    "As an assistive aide, you're focused on providing movie recommendations that resonate with what your users seek.",
    "You take on the role of a helpful assistant, selecting movies that reflect the interests of your users.",
    "Your mission as a helpful assistant is to present movie options tailored to your users' requests.",
    "As an attentive assistant, you make it your job to endorse movies that your users express an interest in."
)

no_rec_r_neg_template = "You didn't recommend anything to me."
no_rec_r_neg = (
    "You haven’t provided any recommendations to me.",
    "No suggestions have been made on your part.",
    "You failed to suggest any titles to me.",
    "I haven't received any movie or TV show recommendations from you.",
    "It seems like you've overlooked recommending any movies or shows to me.",
    "You've not offered any recommendations for movies or TV series.",
    "No movie or TV show recommendations have come my way from you.",
    "You haven't made any movie or TV suggestions to me."
)

hallucination_r_pos_template = "I can find all the recommended {movie}s, nice!"
hallucination_r_pos = (
    "All of the suggested {movie}s are available, which is great!",
    "I've located every one of the recommended {movie}s, awesome!",
    "I managed to find all the {movie}s you recommended, nice going!",
    "Every {movie} that was recommended is findable online, splendid!",
    "It's great that all the recommended {movie}s are accessible!",
    "I have access to all the {movie}s that were recommended, which is fantastic!",
    "All the {movie}s on the recommended list can be found, wonderful!",
    "I'm pleased to find each of the recommended {movie}s available online, nice!"
)

hallucination_r_neg_template = "I can't find some of the recommended {movie}s on the internet."
hallucination_r_neg = (
    "Some of the suggested {movie}s are not discoverable on the internet.",
    "A few of the recommended {movie}s seem to be missing online.",
    "I'm unable to locate a number of the recommended {movie}s on the web.",
    "Several of the {movie}s you recommended aren't available on the internet.",
    "I'm having trouble finding some of the {movie}s you suggested online.",
    "Not all of the recommended {movie}s can be found on the internet.",
    "Some of the {movie}s that were recommended are elusive online.",
    "A portion of the recommended {movie}s appear to be absent from the internet."
)

hallucination_hp_template ="I can find these {movie}s on the internet:"
hallucination_hp = (
    "These {movie}s are available on the internet:",
    "I'm able to locate these {movie}s online:",
    "I have found these {movie}s on the web:",
    "These {movie}s are accessible to me on the internet:",
    "The internet has these {movie}s listed:",
    "I can locate these {movie}s somewhere on the internet:",
    "These {movie}s are present and accounted for online:",
    "I've found these {movie}s available for viewing on the internet:"
)

hallucination_hn_template = "I can't find these {movie}s on the internet:"
hallucination_hn = (
    "These {movie}s aren't available on the internet:",
    "I'm unable to locate these {movie}s online:",
    "These {movie}s are missing from the internet:",
    "I’ve searched online but can't locate these {movie}s:",
    "The internet doesn’t seem to have these {movie}s:",
    "These {movie}s are not to be found on the web:",
    "I can't seem to find these {movie}s anywhere online:",
    "These {movie}s are nowhere to be found on the internet:"
)

hallucination_fp_template = "Recommend {movie}s that I can find online, like:"
hallucination_fp = (
    "Suggest {movie}s that are available online, such as:",
    "Please propose {movie}s that can be located online, for example:",
    "I would appreciate recommendations for {movie}s that are accessible online, like:",
    "Offer up {movie}s I can stream or download online, including:",
    "Focus on recommending {movie}s that are available for online viewing, such as:",
    "Provide suggestions for {movie}s that I can find on the internet, for instance:",
    "Endorse {movie}s that are readily available online, like:",
    "I’m looking for {movie}s that can be found online, such as:"
)

hallucination_fn_template = "Do not recommend {movie}s that I can't find online, like:"
hallucination_fn = (
    "Avoid suggesting {movie}s that are unavailable online, such as:",
    "Please don’t propose {movie}s that aren’t accessible online, for example:",
    "I’d prefer not to get recommendations for {movie}s that can't be located online, like:",
    "Refrain from recommending {movie}s that I can't stream or download, including:",
    "Please exclude {movie}s from your recommendations if they're not online, like:",
    "Ensure not to endorse {movie}s that are not available for online viewing, such as:",
    "Steer clear of advising {movie}s that aren't online, for instance:",
    "I would like to avoid recommendations for {movie}s that are not found online, like:"
)

type_r_pos_template = "What you recommended are {movie}s, nice!"
type_r_pos = (
    "The recommendations you made are {movie}s, great!",
    "You've recommended {movie}s, which is awesome!",
    "The suggestions you provided are {movie}s, nice one!",
    "What's on the recommendation list are {movie}s, fantastic!",
    "Your recommended picks are {movie}s, wonderful!",
    "The titles you suggested are indeed {movie}s, excellent!",
    "Nice, the options you suggested are {movie}s!",
)

type_r_neg_template = "The recommended items are not all {movie}s."
type_r_neg = (
    "Not all of the suggested items are {movie}s.",
    "The recommendations include more than just {movie}s.",
    "Not every recommended item is a {movie}.",
    "The list of recommended items isn't composed solely of {movie}s.",
    "Among the recommended items, there are some non-{movie}s as well.",
    "The suggested items are a mix, not exclusively {movie}s.",
    "There's a variety in the recommendations, not just {movie}s.",
    "The recommendations span beyond just {movie}s."
)

type_hp_template = "These items are indeed all {movie}s: {rest}"
type_hp = (
    "Indeed, each of these items is a {movie}: {rest}",
    "All of these items are, in fact, {movie}s: {rest}",
    "It's confirmed that every item here is a {movie}: {rest}",
    "Without exception, all these items are {movie}s: {rest}",
    "Each one of the items listed is definitely a {movie}: {rest}",
    "True, the entire selection here consists of {movie}s: {rest}",
    "Yes, all these items are categorized as {movie}s: {rest}",
    "Certainly, these items are all {movie}s: {rest}"
)

type_hn_template = "These items are not all {movie}s: {rest}"
type_hn = (
    "Not every one of these items is a {movie}: {rest}",
    "These items include more than just {movie}s: {rest}",
    "Not all items listed here are {movie}s: {rest}",
    "The items here aren't exclusively {movie}s: {rest}",
    "Among these items, not all are {movie}s: {rest}",
    "There's a variety among these items; they're not all {movie}s: {rest}",
    "These items are a mix, with not every one being a {movie}: {rest}",
    "The collection here extends beyond just {movie}s: {rest}"
)

type_fp_template = "Recommend {movie}s, like {rest}"
type_fp = (
    "Suggest {movie}s, such as {rest}",
    "Propose {movie}s, for example {rest}",
    "Advise on {movie}s, similar to {rest}",
    "Offer recommendations for {movie}s, like {rest}",
    "Give examples of {movie}s, including {rest}",
    "Provide me with {movie}s, similar to {rest}",
)

type_fn_template = "Do not recommend items that are not {movie}s, like {rest}"
type_fn = (
    "Avoid suggesting items that aren't {movie}s, such as {rest}",
    "Please don't propose items if they're not {movie}s, like {rest}",
    "Refrain from recommending non-{movie} items, for instance {rest}",
    "Steer clear of advising items that don't fall under {movie}s, including {rest}",
    "Refrain from offering recommendations for items not related to {movie}s, similar to {rest}",
    "Exclude non-{movie} items from suggestions, similar to {rest}",
    "Keep away from indicating items that are not {movie}s, resembling {rest}",
    "Omit items that aren't {movie}s from recommendations, such as {rest}"
)

genre_r_pos_template = "The recommended {movie}s are all {action_comedy_movie}, nice!"
genre_r_pos = (
    "All of the suggested {movie}s are {action_comedy_movie}, great!",
    "Every one of the recommended {movie}s is an {action_comedy_movie}, which is awesome!",
    "The {movie}s you've recommended are exclusively {action_comedy_movie}, nice one!",
    "It's cool that the recommended {movie}s are all {action_comedy_movie}!",
    "Nice to see that each recommended {movie} is a {action_comedy_movie}!",
    "All the {movie}s on the recommendation list are {action_comedy_movie}, wonderful!",
    "Delighted that the recommended {movie}s are all in the {action_comedy_movie} genre, excellent!",
    "The entire list of recommended {movie}s consists of {action_comedy_movie}, which is fantastic!"
)

genre_r_neg_template = "The recommendations are not all {action_comedy_movie}s."
genre_r_neg = (
    "Not every recommendation is an {action_comedy_movie}.",
    "The suggested titles aren't exclusively {action_comedy_movie}s.",
    "The recommendations include more than just {action_comedy_movie}s.",
    "Not all of the recommended picks are {action_comedy_movie}s.",
    "There's a variety in the recommendations, not limited to {action_comedy_movie}s.",
    "The recommendations span a broader range than just {action_comedy_movie}s.",
    "Among the recommended titles, you'll find more than {action_comedy_movie}s.",
    "The list of suggestions contains more than solely {action_comedy_movie}s."
)

genre_hp_template = "These {movie}s are indeed {action_comedy}: {rest}"
genre_hp = (
    "Indeed, these {movie}s are categorized as {action_comedy}: {rest}",
    "Each of these {movie}s is truly an {action_comedy}: {rest}",
    "It is confirmed that these {movie}s fall under the {action_comedy} genre: {rest}",
    "Without a doubt, these {movie}s are {action_comedy}: {rest}",
    "Certainly, all these {movie}s qualify as {action_comedy}: {rest}",
    "These {movie}s can be rightly classified as {action_comedy}: {rest}",
    "Yes, these {movie}s are representative of the {action_comedy} genre: {rest}",
    "Each one of these {movie}s is definitively an {action_comedy}: {rest}"
)

genre_hn_template = "These {movie}s are not {action_comedy}: {rest}"
genre_hn = (
    "These {movie}s do not fall within the {action_comedy} genre: {rest}",
    "These {movie}s aren't classified as {action_comedy}: {rest}",
    "The {movie}s listed here are not categorized as {action_comedy}: {rest}",
    "These {movie}s cannot be considered {action_comedy}: {rest}",
    "None of these {movie}s are {action_comedy}: {rest}",
    "These {movie}s are outside the {action_comedy} category: {rest}",
    "The {movie}s presented here do not belong to the {action_comedy} genre: {rest}",
    "It turns out that these {movie}s are not {action_comedy}: {rest}"
)

genre_fp_template = "Recommend {movie}s that are {action_comedy}, like {rest}"
genre_fp = (
    "Suggest {movie}s falling into the {action_comedy} genre, such as {rest}",
    "Propose {movie}s which are {action_comedy}, for example {rest}",
    "Advise on {movie}s with an {action_comedy} theme, similar to {rest}",
    "Give recommendations for {action_comedy} {movie}s, like {rest}",
    "Offer a list of {movie}s that are {action_comedy}, including {rest}",
    "Identify {movie}s characterized as {action_comedy}, similar to {rest}",
    "Select {movie}s that exemplify the {action_comedy} genre, as in {rest}",
    "Choose {movie}s that are in the {action_comedy} category, like {rest}"
)

genre_fn_template = "Do not recommend {movie}s that are not {action_comedy}, not like {rest}"
genre_fn = (
    "Avoid suggesting {movie}s if they're outside the {action_comedy} genre, unlike {rest}",
    "Please refrain from recommending {movie}s that don't fit the {action_comedy} category, not similar to {rest}",
    "Steer clear of proposing {movie}s that aren't {action_comedy}, in contrast to {rest}",
    "Exclude {movie}s that are not {action_comedy} from your suggestions, not as in {rest}",
    "Do not advise on {movie}s lacking {action_comedy} elements, not resembling {rest}",
    "Omit {movie}s that do not classify as {action_comedy}, not like to {rest}",
    "Refrain from offering {movie}s that diverge from the {action_comedy} type, not comparable to {rest}",
    "Keep away from {movie}s that aren't representative of {action_comedy}, not following the example of {rest}"
)

year_r_pos_template = "The recommended movies are all from the {correct_years}, great!"
year_r_pos = (
    "All the suggested movies hail from the {correct_years}, which is fantastic!",
    "Every one of the recommended films is from the {correct_years}, awesome!",
    "The movies you've recommended are exclusively from the {correct_years}, excellent!",
    "It’s great that all the recommended movies belong to the {correct_years}!",
    "Delighted to see that each movie recommended comes from the {correct_years}!",
    "The entire selection of recommended movies originates from the {correct_years}, wonderful!",
    "All the films on the recommended list are from the {correct_years}, splendid!",
    "The recommended list features movies solely from the {correct_years}, which is perfect!"
)

year_r_neg_template = "The recommended {movie}s are not from the {correct_years}."
year_r_neg = (
    "The suggested {movie}s don't all hail from the {correct_years}.",
    "Some of the recommended {movie}s do not originate from the {correct_years}.",
    "The {movie}s you've recommended aren't all from the {correct_years}.",
    "It turns out the recommended {movie}s are not all from the {correct_years}.",
    "The list of recommended {movie}s are not all from the {correct_years}.",
    "Regrettably, some of the recommended {movie}s fall outside of the {correct_years}.",
    "Some of the recommended {movie}s are unfortunately not all from the specified {correct_years}."
)

year_hp_template = "These {movie}s are indeed from the {correct_years}: {rest}"
year_hp = (
    "Indeed, these {movie}s originate from the {correct_years}: {rest}",
    "These {movie}s are certainly from the {correct_years}: {rest}",
    "It's confirmed that these {movie}s belong to the {correct_years}: {rest}",
    "True, these {movie}s are from the {correct_years}: {rest}",
    "Without question, these {movie}s date back to the {correct_years}: {rest}",
    "Affirmative, these {movie}s were produced in the {correct_years}: {rest}",
    "These {movie}s definitely represent the {correct_years}: {rest}",
    "Yes, these {movie}s are from the era of the {correct_years}: {rest}"
)

year_hn_template = "These {movie}s are not all from the {correct_years}: {rest}"
year_hn = (
    "Not every one of these {movie}s originates from the {correct_years}: {rest}",
    "These {movie}s don't all hail from the {correct_years}: {rest}",
    "A number of these {movie}s fall outside the {correct_years}: {rest}",
    "Some of these {movie}s are not dated within the {correct_years}: {rest}",
    "The release years of these {movie}s don't all match the {correct_years}: {rest}",
    "These {movie}s aren't exclusively from the {correct_years}: {rest}",
    "It's not the case that all these {movie}s were produced in the {correct_years}: {rest}",
    "Each of these {movie}s does not necessarily correspond to the {correct_years}: {rest}"
)

year_fp_template = "Recommend {movie}s that are from {correct_years}, like {rest}"
year_fp = (
    "Suggest {movie}s dating back to {correct_years}, such as {rest}",
    "Propose {movie}s from the era of {correct_years}, for instance {rest}",
    "Advise on {movie}s that originate from {correct_years}, similar to {rest}",
    "Identify {movie}s that were released during {correct_years}, like {rest}",
    "Put forward {movie}s corresponding to {correct_years}, including {rest}",
    "Select {movie}s representative of {correct_years}, exemplified by {rest}",
    "Choose {movie}s which were made in {correct_years}, as in {rest}",
    "Present {movie}s from the {correct_years} period, like {rest}"
)

year_fn_template = "Do not recommend {movie}s that are not from {correct_years}, like {rest}"
year_fn = (
    "Avoid suggesting {movie}s that fall outside of {correct_years}, such as {rest}",
    "Refrain from proposing {movie}s that weren't made in {correct_years}, for example {rest}",
    "Steer clear of recommending {movie}s not produced during {correct_years}, similar to {rest}",
    "Exclude {movie}s from the recommendations if they're not from {correct_years}, including {rest}",
    "Do not put forward {movie}s that do not date back to {correct_years}, like {rest}",
    "Refrain from selecting {movie}s that aren't associated with {correct_years}, as in {rest}",
    "Omit {movie}s from your suggestions if they are not from the period of {correct_years}, exemplified by {rest}",
    "Please do not advise on {movie}s from years other than {correct_years}, such as {rest}"
)

child_friendly_r_pos_template = "The recommended {movie}s are all {child_friendly}, awesome!"
child_friendly_r_pos = (
"Every one of the suggested {movie}s is {child_friendly}, which is fantastic!",
    "All the {movie}s on the recommendation list are {child_friendly}, excellent!",
    "Delighted to see that the recommended {movie}s are entirely {child_friendly}, wonderful!",
    "The {movie}s you’ve recommended are indeed all {child_friendly}, terrific!",
    "It's great to find that each of the {movie}s recommended is {child_friendly}, splendid!",
    "The entire selection of recommended {movie}s is {child_friendly}, how delightful!",
    "Pleased to report that every recommended {movie} is {child_friendly}, superb!"
)

child_friendly_r_neg_template = "The recommended {movie}s are not all {child_friendly}."
child_friendly_r_neg = (
    "Not all of the suggested {movie}s are {child_friendly}.",
    "Some of the recommended {movie}s aren't {child_friendly}.",
    "A few of the recommended {movie}s fall short of being {child_friendly}.",
    "The list of recommended {movie}s includes some that are not {child_friendly}.",
    "Among the recommended {movie}s, not every one is {child_friendly}.",
    "It appears not every {movie} recommended is {child_friendly}.",
    "Not each of the {movie}s on the recommendation list is {child_friendly}.",
    "The recommended {movie}s aren’t all classified as {child_friendly}."
)

child_friendly_hp_template = "These {movie}s are indeed {child_friendly}: {rest}"
child_friendly_hp = (
    "Certainly, these {movie}s are {child_friendly}: {rest}",
    "It's confirmed that these {movie}s are {child_friendly}: {rest}",
    "Absolutely, these {movie}s meet the {child_friendly} criteria: {rest}",
    "These {movie}s are, without a doubt, {child_friendly}: {rest}",
    "True to form, these {movie}s are {child_friendly}: {rest}",
    "Undoubtedly, these {movie}s are {child_friendly}: {rest}",
    "These selected {movie}s are acknowledged as {child_friendly}: {rest}",
    "Each of these {movie}s is verified as {child_friendly}: {rest}"
)

child_friendly_hn_template = "These {movie}s are not {child_friendly}: {rest}"
child_friendly_hn = (
    "Not every one of these {movie}s is {child_friendly}: {rest}",
    "These {movie}s aren't entirely {child_friendly}: {rest}",
    "Some of these {movie}s do not qualify as {child_friendly}: {rest}",
    "Among these {movie}s, some are not {child_friendly}: {rest}",
    "A selection of these {movie}s is not {child_friendly}: {rest}",
    "These {movie}s vary, with not all being {child_friendly}: {rest}",
)

child_friendly_fp_template = "Recommend {movie}s that are {child_friendly}, like {rest}"
child_friendly_fp = (
    "Suggest {movie}s which are classified as {child_friendly}, such as {rest}",
    "Propose a list of {movie}s that carry the {child_friendly} label, for instance {rest}",
    "Provide recommendations for {movie}s that have a {child_friendly} rating, like {rest}",
    "Advise on {movie}s deemed {child_friendly}, including {rest}",
    "Point me towards {movie}s that are known to be {child_friendly}, similar to {rest}",
    "Identify {movie}s appropriate for the {child_friendly} category, exemplified by {rest}",
    "Curate a selection of {movie}s that fit the {child_friendly} criteria, similar to {rest}",
    "Highlight {movie}s that are rated as {child_friendly}, such as {rest}"
)

child_friendly_fn_template = "Do not recommend {movie}s that are not {child_friendly}, like {rest}"
child_friendly_fn = (
    "Avoid suggesting {movie}s which lack a {child_friendly} designation, such as {rest}",
    "Refrain from recommending {movie}s that don’t meet the {child_friendly} standard, like {rest}",
    "Steer clear of {movie}s not recognized as {child_friendly}, for instance {rest}",
    "Exclude {movie}s from the list if they are not {child_friendly}, exemplified by {rest}",
    "Omit {movie}s that do not have a {child_friendly} rating, similar to {rest}",
    "Please do not suggest {movie}s if they’re not {child_friendly}, such as {rest}",
    "Refrain from proposing {movie}s that aren’t considered {child_friendly}, including {rest}",
    "Exclude {movie}s that aren’t labeled as {child_friendly}, like {rest}"
)