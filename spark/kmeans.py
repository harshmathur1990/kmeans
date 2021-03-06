"""
KMeans clustering of Wikipedia pages using Spark.

From: http://ampcamp.berkeley.edu/big-data-mini-course/machine-learning-with-spark.html
"""
import os
import sys
import numpy as np
import time
import datetime

from pyspark import SparkContext

NUMBER_ITERATIONS=10
FILES=["/data/input-judy/random_1000000points_50000clusters.csv",
       "/data/input-judy/random_10000000points_5000clusters.csv",
       "/data/input-judy/random_100000000points_500clusters.csv"
      ]
NUMBER_CLUSTERS=[50000, 5000, 500]
HEADER = ("Run", "File", "Timestamp", "Number_Points", "Number_Clusters" "Time_Type", "Time")
HEADER_CSV = ("%s;%s;%s;%s;%s;%s;\n"%HEADER)
RESULT_DIR="results"
RESULT_FILE_PREFIX="kmeans-spark-"
HADOOP="/root/ephemeral-hdfs/bin/hadoop"
HDFS_WORKING_DIR="/user/root/spark-kmeans"
def setClassPath():
    oldClassPath = os.environ.get('SPARK_CLASSPATH', '')
    cwd = os.path.dirname(os.path.realpath(__file__))
    os.environ['SPARK_CLASSPATH'] = cwd + ":" + oldClassPath


def parseVector(line):
    #print "create vector from: " + str(line)
    return np.array([float(x) for x in line])


def closestPoint(p, centers):
    bestIndex = 0
    closest = float("+inf")
    for i in range(len(centers)):
        dist = np.sum((p - centers[i]) ** 2)
        if dist < closest:
            closest = dist
            bestIndex = i
    return bestIndex


def average(points):
    numVectors = len(points)
    out = np.array(points[0])
    for i in range(2, numVectors):
        out += points[i]
    out = out / numVectors
    return out    



if __name__ == "__main__":
    setClassPath()
    #master = open("/root/spark-ec2/cluster-url").read().strip()
    #masterHostname = open("/root/spark-ec2/masters").read().strip()
    #SparkContext.setSystemProperty('spark.executor.memory', '2g')
    #convergeDist = 1e-5
    master = open("/root/spark-ec2/cluster-url").read().strip()
    masterHostname = open("/root/spark-ec2/masters").read().strip()
    
    os.system(HADOOP + " fs -mkdir " + HDFS_WORKING_DIR)
    #sc = SparkContext("local", "PythonKMeans")
    sc = SparkContext(master, "PythonKMeans")
     
    time_log = []
    for idx, file in enumerate(FILES):
        start = time.time()
        os.system(HADOOP + " fs -put " + file + " " + HDFS_WORKING_DIR)
        hdfs_upload = time.time()-start


        spark_load = time.time() 
        print "Index: " + str(idx) + " File: " + str(file)
        K = NUMBER_CLUSTERS[idx]
        lines = sc.textFile("hdfs://"+masterHostname+":9000/" + HDFS_WORKING_DIR + "/" + os.path.basename(file), 24)
        data = lines.map(lambda x: (x.split(",")[0], parseVector(x.split(",")[0:3]))).cache()
        count = data.count()
        print str(data.first())
        print "Number of records " + str(count)
        load_time = time.time() - spark_load

        result_tuple = (0, file, datetime.datetime.today().isoformat(), count, K)
        hdfs_upload_tuple = result_tuple + ("HDFS Upload", str(hdfs_upload))
        time_log.append("%s;%s;%s;%s;%s;%s;%s\n"%(hdfs_upload_tuple))

        result_tuple = (0, file, datetime.datetime.today().isoformat(), count, K)
        load_time_tuple = result_tuple + ("Load Time", str(load_time))
        time_log.append("%s;%s;%s;%s;%s;%s;%s\n"%(load_time_tuple))

        # TODO: PySpark does not support takeSample(). Use first K points instead.
        centroids = map(lambda (x, y): y, data.take(K))
        tempDist = 1.0
        
        #while tempDist > convergeDist:
        for i in range(0, NUMBER_ITERATIONS):
            start_iteration = time.time()
            closest = data.map(lambda (x, y) : (closestPoint(y, centroids), y))
            pointsGroup = closest.groupByKey()
            newCentroids = pointsGroup.mapValues(lambda x : average(x)).collectAsMap()
            tempDist = sum(np.sum((centroids[x] - y) ** 2) for (x, y) in newCentroids.iteritems())
            for (x, y) in newCentroids.iteritems():
                centroids[x] = y
            print "Finished iteration (delta = " + str(tempDist) + ")"
            sys.stdout.flush()
            iteration_time = time.time()-start_iteration
            iteration_time_tuple = result_tuple + ("Iteration Time", str(iteration_time))
            time_log.append("%s;%s;%s;%s;%s;%s;%s\n"%(iteration_time_tuple))
            
        run_time = time.time()-start
        run_time_tuple = result_tuple + ("Run Time", str(run_time))
        time_log.append("%s;%s;%s;%s;%s;%s;%s\n"%(run_time_tuple))
        
    d =datetime.datetime.now()
    result_filename = RESULT_FILE_PREFIX + d.strftime("%Y%m%d-%H%M%S") + ".csv"
    try:
        os.makedirs(RESULT_DIR)
    except:
        pass
    f = open(os.path.join(RESULT_DIR, result_filename), "w")
    f.write(HEADER_CSV)
    for i in time_log:
        f.write(i)
        
    f.close()
    
    
    #print "Clusters with some articles"
    #numArticles = 10
    #for i in range(0, len(centroids)):
    #  samples = data.filter(lambda (x,y) : closestPoint(y, centroids) == i).take(numArticles)
    #  for (name, features) in samples:
    #    print name
    #  print " "

