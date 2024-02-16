---
hide:
  - toc
  - navigation 
---



The **4th Agriculture-Vision Prize Challenge** aims to promote research in developing innovative and effective algorithms for recognizing agricultural patterns from aerial images. Participants' submissions will be judged and ranked based on model performance.

## Introduction to the Datasets

For this year's CVPR Challenge, we introduce a dynamic blend of two distinct datasets:

- **Extended Agriculture Dataset**: Comprising 105 GB of raw, unprocessed agricultural images across various spectral channels - red, green, blue, and near-infrared (NIR). This unlabeled dataset presents a prime opportunity for semi-supervised learning experiments.

[Download the NEW RAW DATA](https://www.dropbox.com/scl/fo/7yzzc8hqtvaki2y1md6h4/h?rlkey=su71dij6xfb964zfwe1d6kros&dl=0).

- **Original Agriculture Vision Dataset**: A collection of processed and labeled images from past CVPR challenges. This foundational dataset offers structured and annotated data. To download the labeled data, use the AWS command:

```bash
aws s3 cp s3://intelinair-data-releases/agriculture-vision/cvpr_challenge_2021/supervised supervised --no-sign-request --recursive

```

For more details, visit the [Agriculture-Vision Challenge page](https://www.agriculture-vision.com/agriculture-vision-2024/prize-challenge-2024).

## Challenge Overview

The challenge focuses on the strategic utilization of both the unlabeled extended dataset and the labeled original dataset to enhance model performance through semi-supervised learning techniques. The goal is to combine the depth of the unlabeled dataset with the structure of the labeled dataset for superior outcomes.

## Evaluation Criteria

Models will be evaluated using two key sets from previous agriculture vision datasets:

- **Evaluation Set**: Used for initial performance assessment, offering immediate feedback on model effectiveness.
- **Test Set**: The final evaluation will be conducted using a comprehensive test set, establishing the benchmark for model comparison.

The inclusion of the additional unlabeled dataset is expected to significantly improve results, leading to more robust and efficient models. This challenge not only explores the potential of semi-supervised learning in agricultural vision but also aims to advance sustainable agricultural practices.

## Challenge Prizes

A total of $5000 in prizes will be awarded:

1. **1st Place**: $2500 USD
2. **2nd Place**: $1500 USD
3. **3rd Place**: $1000 USD

## Results Submission

The challenge will be hosted on Codalab (link TBA). Participants must [register their team here](#) and then register on the competition Codalab page. Ensure your Codalab account email matches one in the registration form. Each team is limited to one registration per challenge track.

### Submission Requirements

To qualify for prize consideration, submissions must meet the following criteria:

- Metrics in the "results/" folder of the final submission must align with those on the leaderboard.
- Predictions in "results/" should be reproducible with the "code/" and "models/" provided.
- The training process must be reproducible, with retrained models achieving similar performance.
- The test set is strictly off-limits for training or validation.
- Results from models trained with external datasets are ineligible for prizes, though using publicly available pre-trained weights (e.g., ImageNet, Coco) is permitted.

## Important Dates

- **Challenge Opens**: Feb 1, 2024 (11:59 PM PDT)
- **Challenge Paper Submission Deadline**: March 15, 2024 (11:59 PM PDT) *For workshop proceedings*
- **Challenge Results Submission Deadline**: June 3, 2024 (11:59 PM PDT)
- **Challenge Report Submission Deadline**: June 10, 2024 (11:59 PM PDT) *For prize winnings only*
- **Challenge Awards Announcements**: June 19/20, 2024

Note: Final results submission occurs after the paper submission deadline. Teams aiming for the workshop proceedings must submit their results and papers by the first deadline in March. All teams can continue improving their models until the final June deadline, with prize awards based on these last submissions. Top 3 teams must submit a final report by the last deadline to be eligible for prizes.
