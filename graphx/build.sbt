
ThisBuild / scalaVersion := "2.13.18"
ThisBuild / version := "1.0.0"
ThisBuild / organization := "com.cinematch"

lazy val root = (project in file("."))
  .settings(
    name := "cinematch-graphx",

    libraryDependencies ++= Seq(
      "org.apache.spark" %% "spark-core" % "4.3.0",
      "org.apache.spark" %% "spark-sql" % "4.3.0",
      "org.apache.spark" %% "spark-graphx" % "4.3.0"
    ),

    Compile / run / fork := true,

    Compile / run / javaOptions ++= Seq(
      "--add-opens=java.base/java.lang=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
      "--add-opens=java.base/java.io=ALL-UNNAMED",
      "--add-opens=java.base/java.net=ALL-UNNAMED",
      "--add-opens=java.base/java.nio=ALL-UNNAMED",
      "--add-opens=java.base/java.util=ALL-UNNAMED",
      "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED",
      "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED",
      "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
      "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED",
      "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
      "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED"
    )
  )
