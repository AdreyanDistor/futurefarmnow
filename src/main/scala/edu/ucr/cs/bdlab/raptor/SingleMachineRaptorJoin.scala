/*
 * Copyright 2021 University of California, Riverside
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package edu.ucr.cs.bdlab.raptor

import edu.ucr.cs.bdlab.beast.common.BeastOptions
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.{FileSystem, Path}
import org.locationtech.jts.geom.Geometry

object SingleMachineRaptorJoin {

  case class Statistics(min: Float, max: Float, median: Float, sum: Float, mode: Float, stdev: Float, count: Long, mean: Float)

  /**
   * Compute the desired statistics for the given list of values. The computed statistics are (in order):
   *
   *  - maximum
   *  - minimum
   *  - median
   *  - sum
   *  - mode
   *  - stddev
   *  - count
   *  - average (mean)
   *
   * @param inputList the list of values ot compute the statistics for
   * @return
   */
  def statistics(inputList: List[Float]): Statistics = {
    val sortedValues: Array[Float] = inputList.sorted.toArray
    val min: Float = sortedValues(0)
    val max: Float = sortedValues(sortedValues.length - 1)
    val sum: Float = sortedValues.sum
    val mode: Float = sortedValues.groupBy(x => x).toArray.map(x => (x._2.length, x._1)).max._2
    val count: Int = sortedValues.length
    val mean: Float = sum / count
    val stdev: Float = sortedValues.map(x => (x - mean).abs).sum / count
    val median: Float = if (count % 2 == 0) {
      val l = count / 2 - 1
      val r = l + 1
      (sortedValues(l) + sortedValues(r)) / 2
    } else {
      sortedValues(count / 2)
    }

    Statistics( min, max, median, sum, mode, stdev, count, mean )
  }

  def join(rasterFileNames: Array[String], geomArray: Array[Geometry]): Statistics = {
    val intersections: Array[(Int, Intersections)] = rasterFileNames.zipWithIndex.map( {case (rasterFileName: String, index: Int) =>
      val rasterFS: FileSystem = new Path(rasterFileName).getFileSystem(new Configuration())
      val rasterReader = RasterHelper.createRasterReader(rasterFS, new Path(rasterFileName), new BeastOptions())
      val intersections = new Intersections()
      intersections.compute(geomArray, rasterReader.metadata)
      (index, intersections)
    }).filter(_._2.getNumIntersections > 0)
    if (intersections.isEmpty)
      return null
    val intersectionIterator: Iterator[(scala.Long, PixelRange)] = new IntersectionsIterator(intersections.map(_._1), intersections.map(_._2))
    val pixelIterator: Iterator[RaptorJoinResult[scala.Float]] = new PixelIterator(intersectionIterator, rasterFileNames, "0")

    // return statistics
    statistics(pixelIterator.map(x => x.m).filterNot(_ == -9999).toList)
  }

  // join function
  def join(rasterPath: String, geomArray: Array[Geometry]): Statistics =
    join(Array(rasterPath), geomArray)

}
