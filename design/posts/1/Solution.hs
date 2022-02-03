{-# LANGUAGE BlockArguments   #-}
{-# LANGUAGE LambdaCase       #-}
{-# LANGUAGE RebindableSyntax #-}
{-# LANGUAGE TypeOperators    #-}

module Quickhull (

  Point, Line, SegmentedPoints,
  quickhull,

  -- Exported for display
  initialPartition,
  partition,

  -- Exported just for testing
  propagateL, shiftHeadFlagsL, segmentedScanl1,
  propagateR, shiftHeadFlagsR, segmentedScanr1,

) where

import Data.Array.Accelerate
import qualified Prelude                      as P


-- Points and lines in two-dimensional space
--
type Point = (Int, Int)
type Line  = (Point, Point)

-- This algorithm will use a head-flags array to distinguish the different
-- sections of the hull (the two arrays are always the same length).
--
-- A flag value of 'True' indicates that the corresponding point is
-- definitely on the convex hull. The points after the 'True' flag until
-- the next 'True' flag correspond to the points in the same segment, and
-- where the algorithm has not yet decided whether or not those points are
-- on the convex hull.
--
type SegmentedPoints = (Vector Bool, Vector Point)


-- Core implementation
-- -------------------

-- Initialise the algorithm by first partitioning the array into two
-- segments. Locate the left-most (p₁) and right-most (p₂) points. The
-- segment descriptor then consists of the point p₁, followed by all the
-- points above the line (p₁,p₂), followed by the point p₂, and finally all
-- of the points below the line (p₁,p₂).
--
-- To make the rest of the algorithm a bit easier, the point p₁ is again
-- placed at the end of the array.
--
-- We indicate some intermediate values that you might find beneficial to
-- compute.
--
initialPartition :: Acc (Vector Point) -> Acc SegmentedPoints
initialPartition points =
  let
    p1, p2 :: Exp Point
    p1 = the $ minimum points
    p2 = the $ maximum points

    line = T2 p1 p2

    isUpper :: Acc (Vector Bool)
    isUpper = map (pointIsLeftOfLine line) points

    isLower :: Acc (Vector Bool)
    isLower = map (pointIsLeftOfLine (T2 p2 p1)) points

    offsetUpper :: Acc (Vector Int)
    countUpper  :: Acc (Scalar Int)
    T2 offsetUpper countUpper = scanl' (+) 0 $ map (\upper -> upper ? (1, 0)) isUpper

    offsetLower :: Acc (Vector Int)
    countLower  :: Acc (Scalar Int)
    T2 offsetLower countLower = scanl' (+) 0 $ map (\upper -> upper ? (1, 0)) isLower

    destination :: Acc (Vector (Maybe DIM1))
    destination =
      let
        f :: Exp Point -> Exp Bool -> Exp Bool -> Exp Int -> Exp Int -> Exp (Maybe DIM1)
        f p upper lower idxUpper idxLower
          = cond (p == p1) (Just_ $ index1 0)
          $ cond (p == p2) (Just_ $ index1 $ the countUpper + 1)
          $ cond upper     (Just_ $ index1 $ idxUpper + 1)
          $ cond lower     (Just_ $ index1 $ idxLower + 2 + the countUpper)
            Nothing_
      in
      zipWith5 f points isUpper isLower offsetUpper offsetLower

    empty :: Acc (Vector Point)
    empty = fill (index1 $ the countUpper + the countLower + 3) p1

    newPoints :: Acc (Vector Point)
    newPoints = permute const empty (destination !) points

    headFlags :: Acc (Vector Bool)
    headFlags = map (\p -> p == p1 || p == p2) newPoints
    -- Can also be done with `permute`, but that's more difficult
  in
  T2 headFlags newPoints


-- The core of the algorithm processes all line segments at once in
-- data-parallel. This is similar to the previous partitioning step, except
-- now we are processing many segments at once.
--
-- For each line segment (p₁,p₂) locate the point furthest from that line
-- p₃. This point is on the convex hull. Then determine whether each point
-- p in that segment lies to the left of (p₁,p₃) or the right of (p₂,p₃).
-- These points are undecided.
--
partition :: Acc SegmentedPoints -> Acc SegmentedPoints
partition (T2 headFlags points) =
  let
    vecLine :: Acc (Vector Line)
    vecLine = propagateLine (T2 headFlags points)

    headFlagsL = shiftHeadFlagsL headFlags
    headFlagsR = shiftHeadFlagsR headFlags

    furthest :: Acc (Vector Point)
    furthest
      = propagateR headFlagsL
      $ map snd
      $ segmentedScanl1 max headFlagsR
      $ zipWith (\line p -> T2 (nonNormalizedDistance line p) p) vecLine points

    isLeft :: Acc (Vector Bool)
    isLeft = zipWith3 (\p1 pf p -> pointIsLeftOfLine (T2 p1 pf) p) (map fst vecLine) furthest points

    isRight :: Acc (Vector Bool)
    isRight = zipWith3 (\pf p2 p -> pointIsLeftOfLine (T2 pf p2) p) furthest (map snd vecLine) points

    segmentLeftCount :: Acc (Vector Int)
    segmentLeftCount = segmentedScanl1 (+) headFlags $ map (\r -> r ? (1, 0)) isLeft

    segmentRightCount :: Acc (Vector Int)
    segmentRightCount = segmentedScanl1 (+) headFlags $ map (\r -> r ? (1, 0)) isRight

    totalLeft :: Acc (Vector Int)
    totalLeft = propagateR headFlagsL segmentLeftCount

    segmentPermutation :: Acc (Vector (Maybe Int))
    segmentPermutation = zipWith8 f headFlags points furthest isLeft isRight segmentLeftCount segmentRightCount totalLeft
      where
        f :: Exp Bool -> Exp Point -> Exp Point -> Exp Bool -> Exp Bool -> Exp Int -> Exp Int -> Exp Int -> Exp (Maybe Int)
        f flag point furthestP left right leftIdx rightIdx leftCount
          = cond flag                 (Just_ 0)
          $ cond left                 (Just_ $ leftIdx)
          $ cond (point == furthestP) (Just_ $ leftCount + 1)
          $ cond right                (Just_ $ leftCount + 1 + rightIdx)
          Nothing_

    segmentSize :: Acc (Vector Int)
    segmentSize =
      let
        f :: Exp Bool -> Exp Bool -> Exp Int -> Exp Int -> Exp Int
        f flag flagL left right
          = cond (not flagL) 0
          $ cond flag        1 -- Singleton segment
          $ left + right + 2
      in
      zipWith4 f headFlags headFlagsL segmentLeftCount segmentRightCount

    segmentOffset :: Acc (Vector Int)
    numSegments   :: Acc (Scalar Int)
    T2 segmentOffset numSegments = scanl' (+) 0 segmentSize

    permutation :: Acc (Vector (Maybe (Z :. Int)))
    permutation = zipWith f segmentPermutation segmentOffset
      where
        f :: Exp (Maybe Int) -> Exp Int -> Exp (Maybe (Z :. Int))
        f idx offset = idx & match \case
          Nothing_ -> Nothing_
          Just_ i -> Just_ $ index1 $ i + offset

    empty :: Acc (Vector Point)
    empty = fill (index1 $ the numSegments) (T2 0 0)

    newPoints :: Acc (Vector Point)
    newPoints = permute const empty (permutation !) points

    headPermutation :: Acc (Vector (Maybe (Z :. Int)))
    headPermutation =
      let
        f :: Exp Bool -> Exp Point -> Exp Point -> Exp Int -> Exp Int -> Exp (Maybe (Z :. Int))
        f flag p furthestP offset cntLeft
          = cond flag             (Just_ $ index1 offset)
          $ cond (p == furthestP) (Just_ $ index1 $ offset + cntLeft + 1)
          $                       Nothing_
      in
      zipWith5 f headFlags points furthest segmentOffset totalLeft
    -- Similar to `permutation`, but only operates on the values whose head flag becomes True.
    -- Could also be defined as a zipWith over `permutation`.

    emptyFlags :: Acc (Vector Bool)
    emptyFlags = fill (index1 $ the numSegments) (constant False)
    -- Note that you should create this with the new size, not the old size

    trues :: Acc (Vector Bool)
    trues = fill (shape points) (constant True)

    newHeadFlags :: Acc (Vector Bool)
    newHeadFlags = permute const emptyFlags (headPermutation !) trues
    -- Note: cannot be done with a map, you should really use a permute!
  in
  T2 newHeadFlags newPoints


condition :: Acc SegmentedPoints -> Acc (Scalar Bool)
condition (T2 headFlags _) = map not $ and headFlags
-- Iteration should continue as long as there are non-trivial segments, eg not all head flags are true


-- The completed algorithm repeatedly partitions the points until there are
-- no undecided points remaining. What remains is the convex hull.
--
quickhull :: Acc (Vector Point) -> Acc (Vector Point)
quickhull
  = init
  . asnd -- remove the head flags
  . awhile condition partition
  . initialPartition


-- Helper functions
-- ----------------

propagateL :: Elt a => Acc (Vector Bool) -> Acc (Vector a) -> Acc (Vector a)
propagateL = segmentedScanl1 const

propagateR :: Elt a => Acc (Vector Bool) -> Acc (Vector a) -> Acc (Vector a)
propagateR = segmentedScanr1 (P.flip const)

segmentedScanl1 :: Elt a => (Exp a -> Exp a -> Exp a) -> Acc (Vector Bool) -> Acc (Vector a) -> Acc (Vector a)
segmentedScanl1 f headFlags vector = map snd $ scanl1 (segmented f) $ zip headFlags vector

segmentedScanr1 :: Elt a => (Exp a -> Exp a -> Exp a) -> Acc (Vector Bool) -> Acc (Vector a) -> Acc (Vector a)
segmentedScanr1 f headFlags vector = map snd $ scanr1 (P.flip (segmented (P.flip f))) $ zip headFlags vector

shiftHeadFlagsL :: Acc (Vector Bool) -> Acc (Vector Bool)
shiftHeadFlagsL flags = stencil next (function (const True_)) flags
  where
    next :: Stencil3 Bool -> Exp Bool
    next (_,_,r) = r
  -- let I1 n = shape flags
  --     last = n - 1
  --  in imap (\(I1 idx) _ -> idx == last || (flags !! (idx + 1))) flags

shiftHeadFlagsR :: Acc (Vector Bool) -> Acc (Vector Bool)
shiftHeadFlagsR flags = stencil prev (function (const True_)) flags
  where
    prev :: Stencil3 Bool -> Exp Bool
    prev (l,_,_) = l
  -- imap (\(I1 idx) _ -> idx == 0 || (flags !! (idx - 1))) flags

propagateLine :: Acc SegmentedPoints -> Acc (Vector Line)
propagateLine (T2 headFlags points) = zip vecP1 vecP2
  where
    vecP1 = propagateL headFlags points
    vecP2 = propagateR headFlags points

-- Given utility functions
-- -----------------------

pointIsLeftOfLine :: Exp Line -> Exp Point -> Exp Bool
pointIsLeftOfLine (T2 (T2 x1 y1) (T2 x2 y2)) (T2 x y) = nx * x + ny * y > c
  where
    nx = y1 - y2
    ny = x2 - x1
    c  = nx * x1 + ny * y1

nonNormalizedDistance :: Exp Line -> Exp Point -> Exp Int
nonNormalizedDistance (T2 (T2 x1 y1) (T2 x2 y2)) (T2 x y) = nx * x + ny * y - c
  where
    nx = y1 - y2
    ny = x2 - x1
    c  = nx * x1 + ny * y1

segmented :: Elt a => (Exp a -> Exp a -> Exp a) -> Exp (Bool, a) -> Exp (Bool, a) -> Exp (Bool, a)
segmented f (T2 aF aV) (T2 bF bV) = T2 (aF || bF) (bF ? (bV, f aV bV))

