
from pathlib import Path
import time
import csv

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    explode,
    count,
    avg,
    collect_set
)
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from graphframes import GraphFrame
from pyspark.sql.functions import lit, concat, explode



BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "dataset" / "movie_ratings.csv"

RECOMMENDATION_PATH = BASE_DIR / "recommendations.csv"
POPULAR_MOVIES_PATH = BASE_DIR / "popular_movies.csv"
ACTIVE_USERS_PATH = BASE_DIR / "active_users.csv"
RELATIONSHIPS_PATH = BASE_DIR / "user_movie_relationships.csv"
EVALUATION_PATH = BASE_DIR / "evaluation_results.csv"




spark = (
    SparkSession.builder
    .appName("Complete_Movie_Recommendation_System")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")


try:



    print("\n========== DATA INGESTION ==========")

    data = spark.read.csv(
        str(DATA_PATH),
        header=True,
        inferSchema=True
    )

    print("Original Dataset:")
    data.show(5, truncate=False)

    print("Dataset Schema:")
    data.printSchema()

    original_count = data.count()

    print("Original Records:", original_count)




    print("\n========== DATA PREPROCESSING ==========")

    data_cleaned = data.dropna(
        subset=["userId", "movieId", "rating"]
    )

    data_cleaned = (
        data_cleaned
        .withColumn("userId", col("userId").cast("integer"))
        .withColumn("movieId", col("movieId").cast("integer"))
        .withColumn("rating", col("rating").cast("float"))
        .dropna(subset=["userId", "movieId", "rating"])
        .dropDuplicates(["userId", "movieId"])
    )

    data_final = data_cleaned.select(
        "userId",
        "movieId",
        "rating"
    ).cache()

    cleaned_count = data_final.count()

    print("Cleaned Records:", cleaned_count)
    print("Removed Records:", original_count - cleaned_count)

    print("Cleaned Dataset:")
    data_final.show(5)




    print("\n========== TRAIN TEST SPLIT ==========")

    train_data, test_data = data_final.randomSplit(
        [0.8, 0.2],
        seed=42
    )

    train_data = train_data.cache()
    test_data = test_data.cache()

    print("Training Records:", train_data.count())
    print("Testing Records:", test_data.count())



    print("\n========== ALS MODEL ==========")

    als = ALS(
        userCol="userId",
        itemCol="movieId",
        ratingCol="rating",
        rank=10,
        maxIter=10,
        regParam=0.1,
        coldStartStrategy="drop",
        seed=42
    )




    print("\n========== MODEL TRAINING ==========")

    training_start = time.perf_counter()

    model = als.fit(train_data)

    training_time = time.perf_counter() - training_start

    print("ALS Model Trained Successfully!")
    print("Training Time:", round(training_time, 3), "seconds")



    print("\n========== PREDICTIONS ==========")

    prediction_start = time.perf_counter()

    predictions = model.transform(test_data).cache()

    prediction_count = predictions.count()

    prediction_time = time.perf_counter() - prediction_start

    print("Prediction Records:", prediction_count)
    print("Prediction Time:", round(prediction_time, 3), "seconds")

    predictions.select(
        "userId",
        "movieId",
        "rating",
        "prediction"
    ).show(10)



    print("\n========== MODEL EVALUATION ==========")

    rmse_evaluator = RegressionEvaluator(
        labelCol="rating",
        predictionCol="prediction",
        metricName="rmse"
    )

    mae_evaluator = RegressionEvaluator(
        labelCol="rating",
        predictionCol="prediction",
        metricName="mae"
    )

    rmse = rmse_evaluator.evaluate(predictions)
    mae = mae_evaluator.evaluate(predictions)

    print("RMSE:", round(rmse, 4))
    print("MAE:", round(mae, 4))


  

    print("\n========== RANKING EVALUATION ==========")

    # Treat ratings >= 4 as relevant movies.
    relevant_movies = (
        test_data
        .filter(col("rating") >= 4.0)
        .groupBy("userId")
        .agg(
            collect_set("movieId").alias("relevant_movies")
        )
    )

    top_recommendations = model.recommendForAllUsers(10)

    ranking_data = (
        top_recommendations
        .join(relevant_movies, on="userId", how="inner")
        .select("userId", "recommendations", "relevant_movies")
        .collect()
    )

    precisions = []
    recalls = []

    for row in ranking_data:

        recommended = {
            item["movieId"]
            for item in (row["recommendations"] or [])
        }

        actual = set(row["relevant_movies"] or [])

        if not actual:
            continue

        hits = len(recommended.intersection(actual))

        precisions.append(hits / 10)
        recalls.append(hits / len(actual))

    precision_at_10 = (
        sum(precisions) / len(precisions)
        if precisions else 0
    )

    recall_at_10 = (
        sum(recalls) / len(recalls)
        if recalls else 0
    )

    print("Precision@10:", round(precision_at_10, 4))
    print("Recall@10:", round(recall_at_10, 4))

    print("\n========== MOVIE RECOMMENDATIONS ==========")

    recommendation_start = time.perf_counter()

    recommendations = model.recommendForAllUsers(20)

    recommendations = (
        recommendations
        .select(
            col("userId"),
            explode(col("recommendations")).alias("recommendation")
        )
        .select(
            col("userId"),
            col("recommendation.movieId").alias("movieId"),
            col("recommendation.rating").alias("predicted_rating")
        )
    )

    movie_details = data.select(
        "movieId",
        "title",
        "genres"
    ).dropDuplicates(["movieId"])

    final_recommendations = (
        recommendations
        .join(movie_details, on="movieId", how="left")
        .cache()
    )

    recommendation_count = final_recommendations.count()

    recommendation_time = time.perf_counter() - recommendation_start

    print("Total Recommendations:", recommendation_count)
    print(
        "Recommendation Generation Time:",
        round(recommendation_time, 3),
        "seconds"
    )

    final_recommendations.show(10, truncate=False)

    final_recommendations.toPandas().to_csv(
        RECOMMENDATION_PATH,
        index=False
    )

    print("Recommendations saved:", RECOMMENDATION_PATH)



    print("\n========== USER MOVIE RELATIONSHIPS ==========")



    relationships = (
        data_final
        .join(
            movie_details.select("movieId", "title"),
            on="movieId",
            how="left"
        )
        .select(
            "userId",
            "movieId",
            "title",
            "rating"
        )
    )

    relationships.show(10, truncate=False)

    relationships.toPandas().to_csv(
        RELATIONSHIPS_PATH,
        index=False
    )

    print("User-movie relationships saved.")



    print("\n========== POPULAR MOVIES ==========")

    popular_movies = (
        data_final
        .groupBy("movieId")
        .agg(
            count("*").alias("total_ratings"),
            avg("rating").alias("average_rating")
        )
        .join(movie_details, on="movieId", how="left")
        .orderBy(col("total_ratings").desc())
    )

    popular_movies.show(10, truncate=False)

    popular_movies.toPandas().to_csv(
        POPULAR_MOVIES_PATH,
        index=False
    )

    print("Popular movies saved.")


    print("\n========== ACTIVE USERS ==========")

    active_users = (
        data_final
        .groupBy("userId")
        .agg(
            count("*").alias("total_ratings"),
            avg("rating").alias("average_rating")
        )
        .orderBy(col("total_ratings").desc())
    )

    active_users.show(10)

    active_users.toPandas().to_csv(
        ACTIVE_USERS_PATH,
        index=False
    )

    print("Active users saved.")


  

    print("\n========== FINAL EVALUATION REPORT ==========")

    evaluation_results = [{
        "Algorithm": "ALS",
        "Rank": 10,
        "MaxIter": 10,
        "RegParam": 0.1,
        "RMSE": rmse,
        "MAE": mae,
        "Precision_at_10": precision_at_10,
        "Recall_at_10": recall_at_10,
        "Training_Time_Seconds": training_time,
        "Prediction_Time_Seconds": prediction_time,
        "Recommendation_Time_Seconds": recommendation_time,
        "Original_Records": original_count,
        "Cleaned_Records": cleaned_count,
        "Training_Records": train_data.count(),
        "Testing_Records": test_data.count()
    }]

    with open(
        EVALUATION_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=evaluation_results[0].keys()
        )

        writer.writeheader()
        writer.writerows(evaluation_results)

    print("Evaluation results saved:", EVALUATION_PATH)



    print("\n========== PROJECT SUMMARY ==========")

    print("Original Records:", original_count)
    print("Cleaned Records:", cleaned_count)

    print("RMSE:", round(rmse, 4))
    print("MAE:", round(mae, 4))

    print("Precision@10:", round(precision_at_10, 4))
    print("Recall@10:", round(recall_at_10, 4))

    print("Training Time:", round(training_time, 3), "seconds")
    print("Prediction Time:", round(prediction_time, 3), "seconds")

    print(
        "Recommendation Time:",
        round(recommendation_time, 3),
        "seconds"
    )

    print("\nAll operations completed successfully!")


finally:



    spark.stop()

    print("\nSpark Session Stopped Successfully!")
