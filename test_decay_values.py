from geoprompt.equations import (
    linear_cutoff_decay, logistic_decay, cauchy_decay, exponential_decay,
    gaussian_decay, tanh_decay, softplus_decay, cosine_taper_decay,
    rational_quadratic_decay, gompertz_decay, weibull_decay, prompt_decay
)

print("Testing zero distance values:")
print(f"linear_cutoff_decay(0.0, max_distance=1.0) = {linear_cutoff_decay(0.0, max_distance=1.0)}")
print(f"cauchy_decay(0.0, scale=1.0) = {cauchy_decay(0.0, scale=1.0)}")
print(f"exponential_decay(0.0, scale=1.0) = {exponential_decay(0.0, scale=1.0)}")
print(f"gaussian_decay(0.0, scale=1.0) = {gaussian_decay(0.0, scale=1.0)}")
print(f"tanh_decay(0.0, scale=1.0) = {tanh_decay(0.0, scale=1.0)}")
print(f"softplus_decay(0.0, scale=1.0) = {softplus_decay(0.0, scale=1.0)}")
print(f"cosine_taper_decay(0.0, max_distance=1.0) = {cosine_taper_decay(0.0, max_distance=1.0)}")
print(f"rational_quadratic_decay(0.0, scale=1.0, alpha=1.0) = {rational_quadratic_decay(0.0, scale=1.0, alpha=1.0)}")
print(f"gompertz_decay(0.0, scale=1.0, growth=1.0) = {gompertz_decay(0.0, scale=1.0, growth=1.0)}")
print(f"weibull_decay(0.0, scale=1.0, shape=2.0) = {weibull_decay(0.0, scale=1.0, shape=2.0)}")
print(f"prompt_decay(0.0, scale=1.0, power=2.0) = {prompt_decay(0.0, scale=1.0, power=2.0)}")
print(f"logistic_decay(0.0, midpoint=0.0, steepness=1.0) = {logistic_decay(0.0, midpoint=0.0, steepness=1.0)}")
print(f"logistic_decay(0.0, midpoint=1.0, steepness=1.0) = {logistic_decay(0.0, midpoint=1.0, steepness=1.0)}")

print("\nTesting large distance values:")
print(f"cauchy_decay(20.0, scale=1.0) = {cauchy_decay(20.0, scale=1.0)}")
print(f"logistic_decay(20.0, midpoint=0.0, steepness=1.0) = {logistic_decay(20.0, midpoint=0.0, steepness=1.0)}")
