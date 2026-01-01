# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import math
import os
import re
from pathlib import Path
from typing import Any, List, cast

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)

TEMP_DIR = Path('/tmp/earth_science')
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@MCPServer()
class EarthScienceToolkit(BaseToolkit):
    r"""A class representing a toolkit for earth observation science.

    This class provides 104 basic methods for earth observation solutions:
    Index (12), Inversion (18), Perception (15), Analysis (10), Statistics
    (49).
    """

    def calculate_ndvi(self, input_nir_path, input_red_path, output_path):
        r"""Calculate NDVI from NIR and Red band rasters.

        Args:
            input_nir_path (str): Path to Near-Infrared (NIR) band raster.
            input_red_path (str): Path to Red band raster file.
            output_path (str): Relative output path, e.g.
                "question17/ndvi_2022-01-16.tif"

        Returns:
            str: Path to the saved NDVI file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_nir_path) as nir_src:
            nir_band = nir_src.read(1)
            nir_profile = nir_src.profile
        with rasterio.open(input_red_path) as red_src:
            red_band = red_src.read(1)
        nir_band = np.array(nir_band, dtype=np.float32)
        red_band = np.array(red_band, dtype=np.float32)
        denominator = nir_band + red_band + 1e-06
        ndvi = (nir_band - red_band) / denominator
        ndvi_profile = nir_profile.copy()
        ndvi_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **ndvi_profile) as dst:
            dst.write(ndvi.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_ndvi(
        self,
        input_nir_paths: list[str],
        input_red_paths: list[str],
        output_paths: list[str],
    ) -> list[str]:
        r"""Batch-calculate NDVI from multiple pairs of NIR/Red rasters.

        Args:
            input_nir_paths (list[str]): Paths to NIR band rasters.
            input_red_paths (list[str]): Paths to Red band rasters.
            output_paths (list[str]): Relative output paths.

        Returns:
            list[str]: A list of result messages (e.g., saved file paths).
        """
        return [
            self.calculate_ndvi(nir_path, red_path, out_path)
            for nir_path, red_path, out_path in zip(
                input_nir_paths, input_red_paths, output_paths
            )
        ]

    def calculate_ndwi(self, input_nir_path, input_swir_path, output_path):
        r"""Calculate NDWI from NIR and SWIR band rasters.

        Args:
            input_nir_path (str): Path to Near-Infrared (NIR) band raster.
            input_swir_path (str): Path to Short-Wave Infrared (SWIR) raster.
            output_path (str): Relative output path, e.g.
                "question17/ndwi_2022-01-16.tif"

        Returns:
            str: Path to the saved NDWI file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_nir_path) as nir_src:
            nir_band = nir_src.read(1)
            nir_profile = nir_src.profile
        with rasterio.open(input_swir_path) as swir_src:
            swir_band = swir_src.read(1)
        nir_band = np.array(nir_band, dtype=np.float32)
        swir_band = np.array(swir_band, dtype=np.float32)
        denominator = nir_band + swir_band + 1e-06
        ndwi = (nir_band - swir_band) / denominator
        ndwi_profile = nir_profile.copy()
        ndwi_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **ndwi_profile) as dst:
            dst.write(ndwi.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_ndwi(
        self,
        input_nir_paths: list[str],
        input_swir_paths: list[str],
        output_paths: list[str],
    ) -> list[str]:
        r"""Batch-calculate NDWI from multiple pairs of NIR/SWIR rasters.

        Args:
            input_nir_paths (list[str]): Paths to NIR band rasters.
            input_swir_paths (list[str]): Paths to SWIR band rasters.
            output_paths (list[str]): Relative output paths.

        Returns:
            list[str]: A list of result messages (e.g., saved file paths).
        """
        return [
            self.calculate_ndwi(nir_path, swir_path, out_path)
            for nir_path, swir_path, out_path in zip(
                input_nir_paths, input_swir_paths, output_paths
            )
        ]

    def calculate_ndbi(self, input_swir_path, input_nir_path, output_path):
        r"""Calculate NDBI from SWIR and NIR band rasters.

        Args:
            input_swir_path (str): Path to Short-Wave Infrared (SWIR) raster.
            input_nir_path (str): Path to Near-Infrared (NIR) band raster.
            output_path (str): Relative output path, e.g.
                "question17/ndbi_2022-01-16.tif"

        Returns:
            str: Path to the saved NDBI file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_swir_path) as swir_src:
            swir_band = swir_src.read(1)
            swir_profile = swir_src.profile
        with rasterio.open(input_nir_path) as nir_src:
            nir_band = nir_src.read(1)
        swir_band = np.array(swir_band, dtype=np.float32)
        nir_band = np.array(nir_band, dtype=np.float32)
        denominator = swir_band + nir_band + 1e-06
        ndbi = (swir_band - nir_band) / denominator
        ndbi_profile = swir_profile.copy()
        ndbi_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **ndbi_profile) as dst:
            dst.write(ndbi.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_ndbi(
        self,
        input_swir_paths: list[str],
        input_nir_paths: list[str],
        output_paths: list[str],
    ) -> list[str]:
        r"""Batch-calculate NDBI from multiple pairs of SWIR/NIR rasters.

        Args:
            input_swir_paths (list[str]): Paths to SWIR band rasters.
            input_nir_paths (list[str]): Paths to NIR band rasters.
            output_paths (list[str]): Relative output paths.

        Returns:
            list[str]: A list of result messages (e.g., saved file paths).
        """
        return [
            self.calculate_ndbi(swir_path, nir_path, out_path)
            for swir_path, nir_path, out_path in zip(
                input_swir_paths, input_nir_paths, output_paths
            )
        ]

    def calculate_evi(
        self,
        input_nir_path,
        input_red_path,
        input_blue_path,
        output_path,
        G: float = 2.5,
        C1: float = 6,
        C2: float = 7.5,
        L: float = 1,
    ):
        r"""Calculate EVI from NIR, Red, and Blue band rasters.

        Args:
            input_nir_path (str): Path to Near-Infrared (NIR) band raster.
            input_red_path (str): Path to Red band raster file.
            input_blue_path (str): Path to Blue band raster file.
            output_path (str): Relative output path, e.g.
                "question17/evi_2022-01-16.tif"
            G (float, optional): Gain factor. Defaults to 2.5.
            C1 (float, optional): Coefficient 1. Defaults to 6.
            C2 (float, optional): Coefficient 2. Defaults to 7.5.
            L (float, optional): Adjustment factor. Defaults to 1.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_nir_path) as nir_src:
            nir_band = nir_src.read(1)
            nir_profile = nir_src.profile
        with rasterio.open(input_red_path) as red_src:
            red_band = red_src.read(1)
        with rasterio.open(input_blue_path) as blue_src:
            blue_band = blue_src.read(1)
        nir_band = np.array(nir_band, dtype=np.float32)
        red_band = np.array(red_band, dtype=np.float32)
        blue_band = np.array(blue_band, dtype=np.float32)
        denominator = nir_band + C1 * red_band - C2 * blue_band + L + 1e-06
        evi = G * (nir_band - red_band) / denominator
        evi_profile = nir_profile.copy()
        evi_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **evi_profile) as dst:
            dst.write(evi.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_evi(
        self,
        input_nir_paths: list[str],
        input_red_paths: list[str],
        input_blue_paths: list[str],
        output_paths: list[str],
        G: float = 2.5,
        C1: float = 6,
        C2: float = 7.5,
        L: float = 1,
    ) -> list[str]:
        r"""Batch-calculate EVI from multiple sets of NIR/Red/Blue rasters.

        Args:
            input_nir_paths (list[str]): Paths to NIR band rasters.
            input_red_paths (list[str]): Paths to Red band rasters.
            input_blue_paths (list[str]): Paths to Blue band rasters.
            output_paths (list[str]): Relative output paths.
            G, C1, C2, L (float, optional): EVI coefficients.

        Returns:
            list[str]: Result messages from each `calculate_evi` call.
        """
        results: list[str] = []
        for nir_path, red_path, blue_path, out_path in zip(
            input_nir_paths, input_red_paths, input_blue_paths, output_paths
        ):
            res = self.calculate_evi(
                nir_path, red_path, blue_path, out_path, G=G, C1=C1, C2=C2, L=L
            )
            results.append(res)
        return results

    def calculate_nbr(self, input_nir_path, input_swir_path, output_path):
        r"""Calculate NBR from NIR and SWIR band rasters.

        Args:
            input_nir_path (str): Path to Near-Infrared (NIR) band raster.
            input_swir_path (str): Path to Short-Wave Infrared (SWIR) raster.
            output_path (str): Relative output path, e.g.
                "question17/nbr_2022-01-16.tif"

        Returns:
            str: Path to the saved NBR file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_nir_path) as nir_src:
            nir_band = nir_src.read(1)
            nir_profile = nir_src.profile
        with rasterio.open(input_swir_path) as swir_src:
            swir_band = swir_src.read(1)
        nir_band = np.array(nir_band, dtype=np.float32)
        swir_band = np.array(swir_band, dtype=np.float32)
        denominator = nir_band + swir_band + 1e-06
        nbr = (nir_band - swir_band) / denominator
        nbr_profile = nir_profile.copy()
        nbr_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **nbr_profile) as dst:
            dst.write(nbr.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_nbr(
        self,
        input_nir_paths: list[str],
        input_swir_paths: list[str],
        output_paths: list[str],
    ) -> list[str]:
        r"""Batch-calculate NBR from multiple pairs of NIR/SWIR rasters.

        Args:
            input_nir_paths (list[str]): Paths to NIR band rasters.
            input_swir_paths (list[str]): Paths to SWIR band rasters.
            output_paths (list[str]): Relative output paths.

        Returns:
            list[str]: A list of result messages (e.g., saved file paths).
        """
        results: list[str] = []
        for nir_path, swir_path, out_path in zip(
            input_nir_paths, input_swir_paths, output_paths
        ):
            res = self.calculate_nbr(nir_path, swir_path, out_path)
            results.append(res)
        return results

    def calculate_fvc(
        self,
        input_nir_path,
        input_red_path,
        output_path,
        ndvi_min=0.1,
        ndvi_max=0.9,
    ):
        r"""Calculate FVC from NIR and Red band rasters.

        Args:
            input_nir_path (str): Path to Near-Infrared (NIR) band raster.
            input_red_path (str): Path to Red band raster file.
            output_path (str): Relative output path.
            ndvi_min (float): Min NDVI for non-vegetated areas (default: 0.1).
            ndvi_max (float): Max NDVI for fully vegetated areas (default: 0.
            9).

        Returns:
            str: Path to the saved FVC raster file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_nir_path) as nir_src:
            nir_band = nir_src.read(1)
            nir_profile = nir_src.profile
        with rasterio.open(input_red_path) as red_src:
            red_band = red_src.read(1)
        nir_band = np.array(nir_band, dtype=np.float32)
        red_band = np.array(red_band, dtype=np.float32)
        denominator = nir_band + red_band + 1e-06
        ndvi = (nir_band - red_band) / denominator
        fvc = (ndvi - ndvi_min) / (ndvi_max - ndvi_min) * 100
        fvc = np.clip(fvc, 0, 100)
        fvc_profile = nir_profile.copy()
        fvc_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **fvc_profile) as dst:
            dst.write(fvc.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_fvc(
        self,
        input_nir_paths: list[str],
        input_red_paths: list[str],
        output_paths: list[str],
        ndvi_min: float = 0.1,
        ndvi_max: float = 0.9,
    ) -> list[str]:
        r"""Batch-calculate FVC from multiple pairs of NIR/Red rasters.

        Args:
            input_nir_paths (list[str]): Paths to NIR band rasters.
            input_red_paths (list[str]): Paths to Red band rasters.
            output_paths (list[str]): Relative output paths.
            ndvi_min (float, optional): Min NDVI for non-vegetated areas.
            ndvi_max (float, optional): Max NDVI for fully vegetated areas.

        Returns:
            list[str]: A list of result messages (e.g., saved file paths).
        """
        results: list[str] = []
        for nir_path, red_path, out_path in zip(
            input_nir_paths, input_red_paths, output_paths
        ):
            res = self.calculate_fvc(
                nir_path,
                red_path,
                out_path,
                ndvi_min=ndvi_min,
                ndvi_max=ndvi_max,
            )
            results.append(res)
        return results

    def calculate_wri(
        self,
        input_green_path,
        input_red_path,
        input_nir_path,
        input_swir_path,
        output_path,
    ):
        r"""Calculate WRI from Green, Red, NIR, and SWIR band rasters.

        Args:
            input_green_path (str): Path to Green band raster file.
            input_red_path (str): Path to Red band raster file.
            input_nir_path (str): Path to Near-Infrared (NIR) band raster.
            input_swir_path (str): Path to Short-Wave Infrared (SWIR) raster.
            output_path (str): Relative output path.

        Returns:
            str: Path to the saved WRI raster file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_green_path) as green_src:
            green_band = green_src.read(1)
            green_profile = green_src.profile
        with rasterio.open(input_red_path) as red_src:
            red_band = red_src.read(1)
        with rasterio.open(input_nir_path) as nir_src:
            nir_band = nir_src.read(1)
        with rasterio.open(input_swir_path) as swir_src:
            swir_band = swir_src.read(1)
        green_band = np.array(green_band, dtype=np.float32)
        red_band = np.array(red_band, dtype=np.float32)
        nir_band = np.array(nir_band, dtype=np.float32)
        swir_band = np.array(swir_band, dtype=np.float32)
        denominator = nir_band + swir_band + 1e-06
        wri = (green_band + red_band) / denominator
        wri_profile = green_profile.copy()
        wri_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **wri_profile) as dst:
            dst.write(wri.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_wri(
        self,
        input_green_paths: list[str],
        input_red_paths: list[str],
        input_nir_paths: list[str],
        input_swir_paths: list[str],
        output_paths: list[str],
    ) -> list[str]:
        r"""Batch-calculate WRI from multiple raster sets.

        Args:
            input_green_paths (list[str]): Paths to Green band rasters.
            input_red_paths (list[str]): Paths to Red band rasters.
            input_nir_paths (list[str]): Paths to NIR band rasters.
            input_swir_paths (list[str]): Paths to SWIR band rasters.
            output_paths (list[str]): Relative output paths.

        Returns:
            list[str]: A list of result messages (e.g., saved file paths).
        """
        results: list[str] = []
        for green_path, red_path, nir_path, swir_path, out_path in zip(
            input_green_paths,
            input_red_paths,
            input_nir_paths,
            input_swir_paths,
            output_paths,
        ):
            res = self.calculate_wri(
                green_path, red_path, nir_path, swir_path, out_path
            )
            results.append(res)
        return results

    def calculate_ndti(self, input_red_path, input_green_path, output_path):
        r"""Calculate NDTI from Red and Green band rasters.

        Args:
            input_red_path (str): Path to Red band raster file.
            input_green_path (str): Path to Green band raster file.
            output_path (str): Relative output path.

        Returns:
            str: Path to the saved NDTI file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_red_path) as red_src:
            red_band = red_src.read(1)
            red_profile = red_src.profile
        with rasterio.open(input_green_path) as green_src:
            green_band = green_src.read(1)
        red_band = np.array(red_band, dtype=np.float32)
        green_band = np.array(green_band, dtype=np.float32)
        denominator = red_band + green_band + 1e-06
        ndti = (red_band - green_band) / denominator
        ndti_profile = red_profile.copy()
        ndti_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **ndti_profile) as dst:
            dst.write(ndti.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_ndti(
        self,
        input_red_paths: list[str],
        input_green_paths: list[str],
        output_paths: list[str],
    ) -> list[str]:
        r"""Batch-calculate NDTI from multiple pairs of Red/Green rasters.

        Args:
            input_red_paths (list[str]): Paths to Red band rasters.
            input_green_paths (list[str]): Paths to Green band rasters.
            output_paths (list[str]): Relative output paths
                (e.g., "question17/ndti_2022-01-16.tif").

        Returns:
            list[str]: A list of result messages (e.g., saved file paths).
        """
        results: list[str] = []
        for red_path, green_path, out_path in zip(
            input_red_paths, input_green_paths, output_paths
        ):
            res = self.calculate_ndti(red_path, green_path, out_path)
            results.append(res)
        return results

    def calculate_frp(self, input_frp_path, output_path, fire_threshold=0):
        r"""Calculate Fire Radiative Power (FRP) statistics from input raster
        files and save the result to a specified output path.

        Args:
            input_frp_path (str): Path to the FRP raster file.
            output_path (str): relative path for the output raster file,
                e.g. "question17/frp_2022-01-16.tif"
            fire_threshold (float): Minimum FRP value to be considered
                as fire (default: 0).

        Returns:
            str: Path to the saved fire mask file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_frp_path) as frp_src:
            frp_band = frp_src.read(1)
            frp_profile = frp_src.profile
        frp_band = np.array(frp_band, dtype=np.float32)
        fire_mask = (frp_band > fire_threshold).astype(np.uint8)
        output_data = fire_mask * 255
        fire_profile = frp_profile.copy()
        fire_profile.update(dtype=rasterio.uint8, nodata=0)
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **fire_profile) as dst:
            dst.write(output_data, 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_frp(
        self,
        input_frp_paths: list[str],
        output_paths: list[str],
        fire_threshold: float = 0,
    ) -> list[str]:
        r"""Batch-calculate FRP fire masks from multiple raster files.

        Args:
            input_frp_paths (list[str]): Paths to FRP raster files.
            output_paths (list[str]): Relative output paths
                (e.g., "question17/frp_2022-01-16.tif").
            fire_threshold (float, optional): Minimum FRP value to be
                considered as fire. Defaults to 0.

        Returns:
            list[str]: A list of result messages (e.g., saved file paths).
        """
        results: list[str] = []
        for frp_path, out_path in zip(input_frp_paths, output_paths):
            res = self.calculate_frp(
                frp_path, out_path, fire_threshold=fire_threshold
            )
            results.append(res)
        return results

    def calculate_ndsi(
        self, input_green_path: str, input_swir_path: str, output_path: str
    ) -> str:
        r"""Calculate the Normalized Difference Snow Index (NDSI) from input
        raster files and save the result to a specified output path.

        NDSI = (Green - SWIR) / (Green + SWIR)

        Args:
            input_green_path (str): Path to the Green band raster file.
            input_swir_path (str): Path to the SWIR band raster file.
            output_path (str): relative path for the output raster file,
                e.g. "question17/ndsi_2022-01-16.tif"

        Returns:
            str: Path to the output NDSI raster file.
        """
        import numpy as np
        import rasterio
        from scipy.ndimage import zoom

        with rasterio.open(input_green_path) as green_src:
            green_band = green_src.read(1)
            green_profile = green_src.profile
        with rasterio.open(input_swir_path) as swir_src:
            swir_band = swir_src.read(1)
            swir_profile = swir_src.profile
        green_band = np.array(green_band, dtype=np.float32)
        swir_band = np.array(swir_band, dtype=np.float32)
        scale_factor = 0.0001
        green_band = green_band * scale_factor
        swir_band = swir_band * scale_factor
        if green_band.shape != swir_band.shape:
            target_height = min(green_band.shape[0], swir_band.shape[0])
            target_width = min(green_band.shape[1], swir_band.shape[1])
            target_shape = target_height, target_width
            if green_band.shape != target_shape:
                zoom_factors = (
                    target_height / green_band.shape[0],
                    target_width / green_band.shape[1],
                )
                green_band = zoom(green_band, zoom_factors, order=1)
            if swir_band.shape != target_shape:
                zoom_factors = (
                    target_height / swir_band.shape[0],
                    target_width / swir_band.shape[1],
                )
                swir_band = zoom(swir_band, zoom_factors, order=1)
        green_band = np.where(
            (green_band < 0) | (green_band > 1), np.nan, green_band
        )
        swir_band = np.where(
            (swir_band < 0) | (swir_band > 1), np.nan, swir_band
        )
        denominator = green_band + swir_band + 1e-06
        denominator = np.where(
            np.isnan(green_band) | np.isnan(swir_band), np.nan, denominator
        )
        ndsi = (green_band - swir_band) / denominator
        ndsi = np.clip(ndsi, -1, 1)
        output_profile = (
            swir_profile.copy()
            if swir_band.shape[0] <= green_band.shape[0]
            else green_profile.copy()
        )
        output_profile.update(
            dtype=rasterio.float32,
            nodata=-9999,
            compress='lzw',
            height=ndsi.shape[0],
            width=ndsi.shape[1],
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(
            TEMP_DIR / output_path, 'w', **output_profile
        ) as dst:
            dst.write(ndsi.astype(rasterio.float32), 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def calculate_batch_ndsi(
        self,
        green_file_list: list[str],
        swir_file_list: list[str],
        output_path_list: list[str],
    ) -> list[str]:
        """
        Calculate NDSI for multiple pairs of Green and SWIR band images.

        Args:
            green_file_list (list[str]): List of paths to Green band raster
                files.
            swir_file_list (list[str]): List of paths to SWIR band raster
                files.
            output_path_list (list[str]): relative path for the output raster
                file, e.g. ["question17/ndsi_2022-01-16.tif", "question17/
                ndsi_2022-01-16.tif"]

        Returns:
            list[str]: List of paths to the output NDSI raster files.
        """
        if len(green_file_list) != len(swir_file_list):
            raise ValueError('Number of Green and SWIR files must be equal')
        results = []
        for i, (green_path, swir_path) in enumerate(
            zip(green_file_list, swir_file_list)
        ):
            result = self.calculate_ndsi(
                green_path, swir_path, output_path_list[i]
            )
            results.append(result)
        return results

    def calc_extreme_snow_loss_percentage_from_binary_map(
        self, binary_map_path: str
    ) -> float:
        r"""Calculate the percentage of extreme snow and ice loss areas from a
        binary map.

        Args:
            binary_map_path (str):
                Path to the binary raster image where pixels with value 1.0
                represent extreme snow/ice loss areas.

        Returns:
            float:
                The percentage of extreme snow/ice loss pixels relative to all
                valid pixels
                (range: 0.0-1.0).

        Example:
            >>> calc_extreme_snow_loss_percentage_from_binary_map
            ("snow_loss_binary.tif")
            0.27
        """
        import numpy as np

        img = self.read_image(binary_map_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        valid_pixels = flat[~np.isnan(flat)]
        if len(valid_pixels) == 0:
            return 0.0
        extreme_loss_pixels = valid_pixels[valid_pixels == 1.0]
        extreme_loss_percentage = len(extreme_loss_pixels) / len(valid_pixels)
        return float(extreme_loss_percentage)

    def compute_tvdi(
        self, ndvi_path: str, lst_path: str, output_path: str
    ) -> str:
        r"""
        Description:
            Compute the Temperature Vegetation Dryness Index (TVDI) based on
            NDVI and LST raster data.
            TVDI quantifies soil moisture conditions by analyzing the
            relationship between NDVI and LST
            through a trapezoidal space approach. The function fits linear
            regressions for LST maxima
            and minima per NDVI bin and normalizes per-pixel LST values
            accordingly.

        Args:
            ndvi_path (str): Path to the NDVI GeoTIFF file (e.g., MODIS NDVI
            scaled by 0.0001).
            lst_path (str): Path to the LST GeoTIFF file (e.g., MODIS LST
            scaled by 0.02).
            output_path (str): Relative path to save the computed TVDI raster
                            (e.g., "question17/tvdi_2022-01-16.tif").

        Return:
            str: Path to the saved TVDI GeoTIFF file.

        Example:
            >>> compute_tvdi(
            ...     ndvi_path="data/ndvi_2022-01-16.tif",
            ...     lst_path="data/lst_2022-01-16.tif",
            ...     output_path="question17/tvdi_2022-01-16.tif"
            ... )
            'Result saved at question17/tvdi_2022-01-16.tif'
        """
        import numpy as np
        import rasterio
        from scipy.stats import linregress

        with rasterio.open(ndvi_path) as src_ndvi:
            ndvi = src_ndvi.read(1).astype(np.float32) * 0.0001
            profile = src_ndvi.profile
        with rasterio.open(lst_path) as src_lst:
            lst = src_lst.read(1).astype(np.float32) * 0.02
        valid_mask = (ndvi >= 0) & (ndvi <= 1) & (lst > 0)
        if not np.any(valid_mask):
            logger.info(f'Warning: No valid data points in {output_path}')
            tvdi = np.full_like(ndvi, np.nan, dtype=np.float32)
            profile.update(dtype=rasterio.float32, count=1, compress='lzw')
            os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
            with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
                dst.write(tvdi, 1)
            return f'Result saved at {TEMP_DIR / output_path}'
        ndvi_valid = ndvi[valid_mask]
        lst_valid = lst[valid_mask]
        if len(ndvi_valid) < 100:
            logger.info(
                f'Warning: Too few valid data points '
                f'({len(ndvi_valid)}) in {output_path}'
            )
            tvdi = np.full_like(ndvi, np.nan, dtype=np.float32)
            profile.update(dtype=rasterio.float32, count=1, compress='lzw')
            os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
            with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
                dst.write(tvdi, 1)
            return f'Result saved at {TEMP_DIR / output_path}'
        n_bins = 100
        bins = np.linspace(ndvi_valid.min(), ndvi_valid.max(), n_bins + 1)
        ndvi_bin_centers_list: List[Any] = []
        lst_max_vals_list: List[Any] = []
        lst_min_vals_list: List[Any] = []
        for i in range(n_bins):
            bin_mask = (ndvi_valid >= bins[i]) & (ndvi_valid < bins[i + 1])
            if np.any(bin_mask):
                ndvi_bin_centers_list.append((bins[i] + bins[i + 1]) / 2)
                lst_max_vals_list.append(np.max(lst_valid[bin_mask]))
                lst_min_vals_list.append(np.min(lst_valid[bin_mask]))
        if len(ndvi_bin_centers_list) < 2:
            logger.info(
                f'Warning: Not enough data bins for regression in '
                f'{output_path}'
            )
            tvdi = np.full_like(ndvi, np.nan, dtype=np.float32)
            profile.update(dtype=rasterio.float32, count=1, compress='lzw')
            os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
            with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
                dst.write(tvdi, 1)
            return f'Result saved at {TEMP_DIR / output_path}'
        ndvi_bin_centers = np.array(ndvi_bin_centers_list)
        lst_max_vals = np.array(lst_max_vals_list)
        lst_min_vals = np.array(lst_min_vals_list)
        slope_max, intercept_max, _, _, _ = linregress(
            ndvi_bin_centers, lst_max_vals
        )
        slope_min, intercept_min, _, _, _ = linregress(
            ndvi_bin_centers, lst_min_vals
        )
        lst_max = ndvi * slope_max + intercept_max
        lst_min = ndvi * slope_min + intercept_min
        denominator = lst_max - lst_min
        denominator[denominator == 0] = 1e-06
        tvdi = (lst - lst_min) / denominator
        tvdi = np.clip(tvdi, 0, 1).astype(np.float32)
        tvdi[~valid_mask] = np.nan
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(tvdi, 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def band_ratio(
        self,
        sur_refl_b02_path: str,
        sur_refl_b05_path: str,
        sur_refl_b17_path: str,
        sur_refl_b18_path: str,
        sur_refl_b19_path: str,
        output_path: str,
    ) -> str:
        r"""
        Description:
            Compute a Precipitable Water Vapor (PWV) image from MODIS surface
            reflectance bands
            using the band ratio method.
            This method interpolates atmospheric window reflectance between 0.
            865 µm and 1.240 µm,
            computes transmittance in water vapor absorption bands (0.905, 0.
            936, 0.940 µm),
            and derives PWV in centimeters.
            The output GeoTIFF contains four bands:
                1. PWV
                2. T17 (transmittance at 0.905 µm)
                3. T18 (transmittance at 0.936 µm)
                4. T19 (transmittance at 0.940 µm)

        Args:
            sur_refl_b02_path (str): Path to MODIS surface reflectance band
            sur_refl_b02 (0.865 µm) GeoTIFF.
            sur_refl_b05_path (str): Path to MODIS surface reflectance band
            sur_refl_b05 (1.240 µm) GeoTIFF.
            sur_refl_b17_path (str): Path to MODIS surface reflectance band
            sur_refl_b17 (0.905 µm) GeoTIFF.
            sur_refl_b18_path (str): Path to MODIS surface reflectance band
            sur_refl_b18 (0.936 µm) GeoTIFF.
            sur_refl_b19_path (str): Path to MODIS surface reflectance band
            sur_refl_b19 (0.940 µm) GeoTIFF.
            output_path (str): Relative output path for the PWV GeoTIFF, e.g.
            "question17/pwv_2022-01-16.tif".

        Return:
            str: Full path to the saved PWV GeoTIFF.

        Example:
            result = band_ratio(
                sur_refl_b02_path="data/MODIS_sur_refl_b02.tif",
                sur_refl_b05_path="data/MODIS_sur_refl_b05.tif",
                sur_refl_b17_path="data/MODIS_sur_refl_b17.tif",
                sur_refl_b18_path="data/MODIS_sur_refl_b18.tif",
                sur_refl_b19_path="data/MODIS_sur_refl_b19.tif",
                output_path="question17/pwv_2022-01-16.tif"
            )
            logger.info(result)
            # Output: "Result saved at TEMP_DIR/question17/pwv_2022-01-16.tif"
        """
        import numpy as np
        import rasterio

        with (
            rasterio.open(sur_refl_b02_path) as src02,
            rasterio.open(sur_refl_b05_path) as src05,
            rasterio.open(sur_refl_b17_path) as src17,
            rasterio.open(sur_refl_b18_path) as src18,
            rasterio.open(sur_refl_b19_path) as src19,
        ):
            b02 = src02.read(1).astype(np.float32)
            b05 = src05.read(1).astype(np.float32)
            b17 = src17.read(1).astype(np.float32)
            b18 = src18.read(1).astype(np.float32)
            b19 = src19.read(1).astype(np.float32)
            profile = src02.profile
        λ2, λ5 = 0.865, 1.24
        λ17, λ18, λ19 = 0.905, 0.936, 0.94
        a = (b05 - b02) / (λ5 - λ2)
        b = b02 - a * λ2
        rho17 = a * λ17 + b
        rho18 = a * λ18 + b
        rho19 = a * λ19 + b
        T17 = np.divide(b17, rho17, out=np.zeros_like(b17), where=rho17 != 0)
        T18 = np.divide(b18, rho18, out=np.zeros_like(b18), where=rho18 != 0)
        T19 = np.divide(b19, rho19, out=np.zeros_like(b19), where=rho19 != 0)
        k = 0.03
        with np.errstate(divide='ignore', invalid='ignore'):
            PWV = -np.log(T18) / k
            PWV[np.isnan(PWV)] = 0
            PWV[PWV < 0] = 0
        out_data = np.stack([PWV, T17, T18, T19], axis=0).astype(np.float32)
        profile.update(dtype=rasterio.float32, count=4, compress='lzw')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(out_data)
        return f'Result saved at {TEMP_DIR / output_path}'

    def lst_single_channel(
        self, bt_path: str, red_path: str, nir_path: str, output_path: str
    ) -> str:
        """
        Description:
            Estimate Land Surface Temperature (LST) using the Single-Channel
            method.
            This approach calculates LST from thermal brightness temperature
            and adjusts
            for surface emissivity estimated using NDVI derived from RED and
            NIR bands.
            It is suitable for single thermal band sensors such as Landsat 8
            TIRS.

        Args:
            bt_path (str): Path to the Brightness Temperature GeoTIFF (Kelvin).
            red_path (str): Path to the RED band GeoTIFF (e.g., Landsat 8 Band
            4).
            nir_path (str): Path to the NIR band GeoTIFF (e.g., Landsat 8 Band
            5).
            output_path (str): Relative path for the output LST GeoTIFF,
                            e.g. "question17/lst_2022-01-16.tif".

        Return:
            str: Full path to the saved LST GeoTIFF.

        Example:
            result = lst_single_channel(
                bt_path="data/Landsat8_BT.tif",
                red_path="data/Landsat8_B4.tif",
                nir_path="data/Landsat8_B5.tif",
                output_path="question17/lst_2022-01-16.tif"
            )
            logger.info(result)
            # Output: "Result saved at TEMP_DIR/question17/lst_2022-01-16.tif"
        """

        import numpy as np
        import rasterio

        def read_band(path):
            with rasterio.open(path) as src:
                band = src.read(1).astype(np.float32)
                profile = src.profile
                band[band < 0] = np.nan
            return band, profile

        bt, profile = read_band(bt_path)
        red, _ = read_band(red_path)
        nir, _ = read_band(nir_path)
        ndvi = (nir - red) / (nir + red + 1e-06)
        emissivity = np.where(
            ndvi > 0.7, 0.99, np.where(ndvi < 0.2, 0.96, 0.97 + 0.003 * ndvi)
        )
        wavelength = 10.9
        c2 = 14387.7
        lst = bt / (1 + wavelength * bt / c2 * np.log(emissivity))
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(lst.astype(np.float32), 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def lst_multi_channel(
        self, band31_path: str, band32_path: str, output_path: str
    ) -> str:
        """
        Description:
            Estimate Land Surface Temperature (LST) using the multi-channel
            algorithm.
            This method combines two thermal infrared bands (typically at ~11
            μm and ~12 μm)
            to reduce atmospheric effects and improve LST estimation accuracy.

        Args:
            band31_path (str): Path to local GeoTIFF file for thermal band 31
                (~11 μm).
            band32_path (str): Path to local GeoTIFF file for thermal band 32
                (~12 μm).
            output_path (str): Relative path for the output LST GeoTIFF,
                e.g. "question17/lst_2022-01-16.tif".

        Return:
            str: Full path to the saved LST GeoTIFF.

        Example:
            result = lst_multi_channel(
                band31_path="data/MODIS_Band31.tif",
                band32_path="data/MODIS_Band32.tif",
                output_path="question17/lst_2022-01-16.tif"
            )
            logger.info(result)
            # Output: "Result saved at TEMP_DIR/question17/lst_2022-01-16.tif"
        """
        import numpy as np
        import rasterio

        with rasterio.open(band31_path) as src31:
            band31 = src31.read(1).astype(np.float32)
            profile = src31.profile
        with rasterio.open(band32_path) as src32:
            band32 = src32.read(1).astype(np.float32)
        a = 1.022
        b = 0.47
        c = 0.43
        lst = a * band31 + b * (band31 - band32) + c
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(lst.astype(np.float32), 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def split_window(
        self,
        band31_path: str,
        band32_path: str,
        emissivity31_path: str,
        emissivity32_path: str,
        parameter: str,
        output_path: str,
    ) -> str:
        r"""Description:
            Estimate **Land Surface Temperature (LST)** or **Precipitable
            Water Vapor (PWV)**
            using the split-window algorithm.
            The method leverages two thermal infrared bands (~11 μm and ~12 μm)
            and emissivity data to correct atmospheric effects and retrieve
            accurate surface or atmospheric Args.
            Only one parameter is computed based on the user-selected
            `parameter`.

        Args:
            band31_path (str): Path to thermal band 31 GeoTIFF (~11 μm).
            band32_path (str): Path to thermal band 32 GeoTIFF (~12 μm).
            emissivity31_path (str): Path to emissivity band 31 GeoTIFF.
            emissivity32_path (str): Path to emissivity band 32 GeoTIFF.
            parameter (str): Specify either `"LST"` for Land Surface
                Temperature or `"PWV"` for Precipitable Water Vapor.
            output_path (str): Relative path for the output raster file,
                e.g. `"question17/lst_2022-01-16.tif"`.

        Return:
            str: Full path to the saved GeoTIFF containing the selected
                parameter.

        Example:
            # Example 1: Retrieve LST
            result = split_window(
                band31_path="data/TIRS_Band31.tif",
                band32_path="data/TIRS_Band32.tif",
                emissivity31_path="data/Emis_B31.tif",
                emissivity32_path="data/Emis_B32.tif",
                parameter="LST",
                output_path="question17/lst_2022-01-16.tif"
            )
            logger.info(result)
            # Output: "Result saved at TEMP_DIR/question17/lst_2022-01-16.tif"

            # Example 2: Retrieve PWV
            result = split_window(
                band31_path="data/TIRS_Band31.tif",
                band32_path="data/TIRS_Band32.tif",
                emissivity31_path="data/Emis_B31.tif",
                emissivity32_path="data/Emis_B32.tif",
                parameter="PWV",
                output_path="question17/pwv_2022-01-16.tif"
            )
            logger.info(result)
            # Output: "Result saved at TEMP_DIR/question17/pwv_2022-01-16.tif"
        """
        import numpy as np
        import rasterio

        with rasterio.open(band31_path) as src31:
            band31 = src31.read(1).astype(np.float32)
            profile = src31.profile
        with rasterio.open(band32_path) as src32:
            band32 = src32.read(1).astype(np.float32)
        with rasterio.open(emissivity31_path) as src_e31:
            e31 = src_e31.read(1).astype(np.float32)
            logger.info(
                f'Emissivity31 Original range: '
                f'{np.nanmin(e31):.4f} to {np.nanmax(e31):.4f}'
            )
            e31 = e31 * 0.002 + 0.49
            logger.info(
                f'Emissivity31 Corrected range: '
                f'{np.nanmin(e31):.4f} to {np.nanmax(e31):.4f}'
            )
        with rasterio.open(emissivity32_path) as src_e32:
            e32 = src_e32.read(1).astype(np.float32)
            logger.info(
                f'Emissivity32 Original range: '
                f'{np.nanmin(e32):.4f} to {np.nanmax(e32):.4f}'
            )
            e32 = e32 * 0.002 + 0.49
            logger.info(
                f'Emissivity32 Corrected range: '
                f'{np.nanmin(e32):.4f} to {np.nanmax(e32):.4f}'
            )
        delta_T = band31 - band32
        logger.info(
            f'Temperature difference ΔT range: '
            f'{np.nanmin(delta_T):.4f} to {np.nanmax(delta_T):.4f}'
        )
        eps_mean = (e31 + e32) / 2
        logger.info(
            f'Mean emissivity range: {np.nanmin(eps_mean):.4f} to '
            f'{np.nanmax(eps_mean):.4f}'
        )
        delta_eps = e31 - e32
        logger.info(
            f'Emissivity difference Δε range: {np.nanmin(delta_eps):.4f} '
            f'to {np.nanmax(delta_eps):.4f}'
        )
        eps_mean = np.clip(eps_mean, 0.8, 1.0)
        if parameter.upper() == 'LST':
            C0, C1, C2, C3, C4 = 0.268, 1.378, 0.183, 54.3, -2.238
            t31_c = band31 - 273.15
            term1 = C0
            term2 = C1 * t31_c
            term3 = C2 * t31_c**2 / 1000
            term4 = (C3 + C4 * delta_T) * (1 - eps_mean)
            term5 = (C3 + C4 * delta_T) * delta_eps
            lst = term1 + term2 + term3 + term4 + term5
            lst = lst + 273.15
            lst = np.where((lst < 200) | (lst > 350), np.nan, lst)
            output = lst.astype(np.float32)
            out_band_name = 'LST'
        elif parameter.upper() == 'PWV':
            pwv = delta_T / (band31 * eps_mean) * 100
            output = pwv.astype(np.float32)
            out_band_name = 'PWV'
        else:
            raise ValueError("Parameter must be either 'LST' or 'PWV'")
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(output, 1)
        logger.info(f'\nFinal {out_band_name} statistics:')
        logger.info(f'Min: {np.nanmin(output):.2f}')
        logger.info(f'Max: {np.nanmax(output):.2f}')
        logger.info(f'Mean: {np.nanmean(output):.2f}')
        logger.info(
            f'Valid data percent: '
            f'{np.sum(~np.isnan(output)) / output.size * 100:.2f}%'
        )
        return f'Result saved at {TEMP_DIR / output_path}'

    def temperature_emissivity_separation(
        self,
        tir_band_paths: list[str],
        representative_band_index: int,
        output_path: str,
    ) -> str:
        """
        Description:
            Estimate Land Surface Temperature (LST) using the Temperature
            Emissivity Separation (TES)
            algorithm with empirical emissivity estimation. Outputs a
            multi-band raster containing LST,
            emissivity, and emissivity variation (Δε).

        Args:
            tir_band_paths (list[str]): List of paths to Thermal Infrared
            (TIR) GeoTIFFs (e.g., ASTER Bands 10-14).
            representative_band_index (int): Index of the TIR band used as the
            reference brightness temperature (e.g., 3 for Band 13).
            output_path (str): Relative path for saving the output raster file
            (e.g., "question17/lst_2022-01-16.tif").

        Return:
            str: Path to the saved GeoTIFF file containing:
                - Band 1: LST (K)
                - Band 2: Emissivity (ε)
                - Band 3: Emissivity variation (Δε)

        Example:
            >>> temperature_emissivity_separation(
            ...     ["ASTER_B10.tif", "ASTER_B11.tif", "ASTER_B12.tif",
            "ASTER_B13.tif", "ASTER_B14.tif"],
            ...     representative_band_index=3,
            ...     output_path="question17/lst_2022-01-16.tif"
            ... )
            'Result saved at question17/lst_2022-01-16.tif'
        """
        import numpy as np
        import rasterio

        c2 = 14387.7
        wavelength = 10.6
        with rasterio.open(tir_band_paths[representative_band_index]) as src:
            rep_band = src.read(1).astype(np.float32)
            profile = src.profile.copy()
            valid_mask = (rep_band > 0) & (rep_band < 1000)
        bands_data = []
        for path in tir_band_paths:
            with rasterio.open(path) as src:
                band = src.read(1).astype(np.float32)
                band[~valid_mask] = np.nan
                bands_data.append(band)
        bands_stack = np.stack(bands_data, axis=0)
        masked_stack = np.ma.masked_invalid(bands_stack)
        band_max = np.ma.max(masked_stack, axis=0).filled(np.nan)
        band_min = np.ma.min(masked_stack, axis=0).filled(np.nan)
        delta_epsilon = band_max - band_min
        emissivity = 0.982 - 0.072 * delta_epsilon
        emissivity = np.clip(emissivity, 0.85, 0.999)
        Tb = bands_stack[representative_band_index]
        Tb[~valid_mask] = np.nan
        valid_calc = (
            (Tb > 0) & (emissivity > 0) & ~np.isnan(Tb) & ~np.isnan(emissivity)
        )
        lst = np.full_like(Tb, np.nan)
        lst[valid_calc] = Tb[valid_calc] / (
            1
            + wavelength * Tb[valid_calc] / c2 * np.log(emissivity[valid_calc])
        )
        out_stack = np.stack([lst, emissivity, delta_epsilon], axis=0).astype(
            np.float32
        )
        profile.update(
            dtype=rasterio.float32, count=3, compress='lzw', nodata=np.nan
        )
        out_full_path = TEMP_DIR / output_path
        os.makedirs(out_full_path.parent, exist_ok=True)
        with rasterio.open(out_full_path, 'w', **profile) as dst:
            dst.write(out_stack)
            dst.set_band_description(1, 'LST (K)')
            dst.set_band_description(2, 'Emissivity (ε)')
            dst.set_band_description(3, 'Emissivity Variation (Δε)')
        return f'Result saved at {out_full_path}'

    def modis_day_night_lst(
        self,
        BT_day_path: str,
        BT_night_path: str,
        Emis_day_path: str,
        Emis_night_path: str,
        output_path: str,
    ) -> str:
        """
        Description:
            Estimate Land Surface Temperature (LST) from MODIS Day and Night
            brightness temperatures
            using a single-channel correction algorithm. Performs resampling,
            scaling, and filtering
            of emissivity and brightness temperature bands to output a
            six-band GeoTIFF.

        Args:
            BT_day_path (str): Path to local MODIS Brightness Temperature Day
                GeoTIFF.
            BT_night_path (str): Path to local MODIS Brightness Temperature
                Night GeoTIFF.
            Emis_day_path (str): Path to MODIS Emissivity Day GeoTIFF (scaled
                by 0.002, offset by 0.49).
            Emis_night_path (str): Path to MODIS Emissivity Night GeoTIFF
                (scaled by 0.002, offset by 0.49).
            output_path (str): Relative path for saving the output raster file
                (e.g., "question17/lst_2022-01-16.tif").

        Return:
            str: Path to the exported GeoTIFF with six bands:
                - Band 1: LST (Day)
                - Band 2: LST (Night)
                - Band 3: BT (Day)
                - Band 4: BT (Night)
                - Band 5: Emissivity (Day)
                - Band 6: Emissivity (Night)

        Example:
            >>> modis_day_night_lst(
            ...     BT_day_path="MODIS_BT_Day.tif",
            ...     BT_night_path="MODIS_BT_Night.tif",
            ...     Emis_day_path="MODIS_Emis_Day.tif",
            ...     Emis_night_path="MODIS_Emis_Night.tif",
            ...     output_path="question17/lst_2022-01-16.tif"
            ... )
            'Result saved at question17/lst_2022-01-16.tif'
        """

        import numpy as np
        import rasterio

        def resample_to_reference(
            src_data: np.ndarray, src_profile: dict, ref_profile: dict
        ) -> np.ndarray:
            src_height, src_width = src_data.shape
            dst_height = ref_profile['height']
            dst_width = ref_profile['width']
            scale_h = dst_height / src_height
            scale_w = dst_width / src_width
            dst_data = np.zeros((dst_height, dst_width), dtype=src_data.dtype)
            for i in range(dst_height):
                for j in range(dst_width):
                    src_i = min(int(i / scale_h), src_height - 1)
                    src_j = min(int(j / scale_w), src_width - 1)
                    dst_data[i, j] = src_data[src_i, src_j]
            return dst_data

        MIN_TEMP = 270
        MAX_TEMP = 325
        with rasterio.open(BT_day_path) as src:
            BT_day = src.read(1).astype(np.float32)
            BT_day = np.where(
                (BT_day > MAX_TEMP) | (BT_day < MIN_TEMP), np.nan, BT_day
            )
            ref_profile = src.profile.copy()
        with rasterio.open(BT_night_path) as src:
            BT_night_raw = src.read(1).astype(np.float32)
            BT_night_raw = np.where(
                (BT_night_raw > MAX_TEMP) | (BT_night_raw < MIN_TEMP),
                np.nan,
                BT_night_raw,
            )
            BT_night = resample_to_reference(
                BT_night_raw, src.profile, ref_profile
            )
        with rasterio.open(Emis_day_path) as src:
            Emis_day_raw = src.read(1).astype(np.float32)
            Emis_day_raw = Emis_day_raw * 0.002 + 0.49
            Emis_day = resample_to_reference(
                Emis_day_raw, src.profile, ref_profile
            )
        with rasterio.open(Emis_night_path) as src:
            Emis_night_raw = src.read(1).astype(np.float32)
            Emis_night_raw = Emis_night_raw * 0.002 + 0.49
            Emis_night = resample_to_reference(
                Emis_night_raw, src.profile, ref_profile
            )
        Emis_day_clipped = np.clip(Emis_day, 0.5, 1.0)
        Emis_night_clipped = np.clip(Emis_night, 0.5, 1.0)
        wavelength = 11.0
        c2 = 14387.7
        LST_day = BT_day / (
            1 + wavelength * BT_day / c2 * np.log(Emis_day_clipped)
        )
        LST_night = BT_night / (
            1 + wavelength * BT_night / c2 * np.log(Emis_night_clipped)
        )
        LST_day = np.where(
            (LST_day > MAX_TEMP) | (LST_day < MIN_TEMP), np.nan, LST_day
        )
        LST_night = np.where(
            (LST_night > MAX_TEMP) | (LST_night < MIN_TEMP), np.nan, LST_night
        )
        out_stack = np.stack(
            [LST_day, LST_night, BT_day, BT_night, Emis_day, Emis_night],
            axis=0,
        ).astype(np.float32)
        profile = ref_profile.copy()
        profile.update(count=6, dtype=rasterio.float32, compress='lzw')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(out_stack)
        return f'Result saved at {TEMP_DIR / output_path}'

    def ttm_lst(
        self,
        tir_band_paths: list[str],
        output_path: str,
        wavelengths: list[float] | None = None,
    ) -> str:
        """Estimate LST and emissivity using Three-Temperature Method.

        Reads three thermal infrared (TIR) bands, performs filtering,
        applies empirical atmospheric correction, and outputs a
        three-band GeoTIFF with LST and emissivity estimates.

        Args:
            tir_band_paths (list[str]): Paths to three TIR band GeoTIFFs
                (e.g., ASTER B10, B11, B12).
            output_path (str): Relative path to save the output raster.
            wavelengths (list[float], optional): Central wavelengths (μm)
                for each band. Defaults to [8.3, 8.65, 9.1].

        Return:
            str: Path to exported GeoTIFF with LST (K) and emissivity bands.

        Example:
            >>> ttm_lst(["B10.tif", "B11.tif", "B12.tif"], "out/lst.tif")
            'Result saved at out/lst.tif'
        """
        import numpy as np
        import rasterio

        if wavelengths is None:
            wavelengths = [8.3, 8.65, 9.1]
        logger.info('Reading input bands...')
        bands_data = []
        profile = None
        for path in tir_band_paths:
            with rasterio.open(path) as src:
                band = src.read(1).astype(np.float32)
                bands_data.append(band)
                if profile is None:
                    profile = src.profile.copy()
        B1, B2, B3 = bands_data
        shape = B1.shape
        logger.info(f'Image size: {shape[1]} x {shape[0]}')
        valid_mask = (
            (B1 > 240)
            & (B1 < 340)
            & (B2 > 240)
            & (B2 < 340)
            & (B3 > 240)
            & (B3 < 340)
        )
        lst = np.full(shape, np.nan, dtype=np.float32)
        eps1_arr = np.full(shape, np.nan, dtype=np.float32)
        eps2_arr = np.full(shape, np.nan, dtype=np.float32)
        valid_indices = np.where(valid_mask)
        logger.info(f'Number of valid pixels: {len(valid_indices[0])}')
        weights = np.array([0.3, 0.3, 0.4])
        lst_valid = (
            B1[valid_mask] * weights[0]
            + B2[valid_mask] * weights[1]
            + B3[valid_mask] * weights[2]
        )
        lst_valid += 2.0
        lst[valid_mask] = lst_valid
        eps_mean = 0.95
        eps1_arr[valid_mask] = eps_mean
        eps2_arr[valid_mask] = eps_mean
        logger.info('Saving results...')
        if profile is None:
            raise RuntimeError('Failed to read profile from input bands')
        profile.update(
            count=3, dtype=rasterio.float32, compress='lzw', nodata=np.nan
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(lst, 1)
            dst.write(eps1_arr, 2)
            dst.write(eps2_arr, 3)
        logger.info(
            f'Processing complete! Results saved to: {TEMP_DIR / output_path}'
        )
        valid_temps = lst[~np.isnan(lst)]
        logger.info('\nTemperature Statistics:')
        logger.info(f'Minimum: {np.min(valid_temps):.2f}K')
        logger.info(f'Maximum: {np.max(valid_temps):.2f}K')
        logger.info(f'Mean: {np.mean(valid_temps):.2f}K')
        logger.info(f'Median: {np.median(valid_temps):.2f}K')
        return f'Result saved at {TEMP_DIR / output_path}'

    def calculate_mean_lst_by_ndvi(
        self,
        red_paths: (str | list[str]),
        nir_paths: (str | list[str]),
        lst_paths: (str | list[str]),
        ndvi_threshold: float,
        mode: str = 'above',
    ) -> float:
        """
        Calculate the average Land Surface Temperature (LST) across multiple
        images where NDVI is either above or below a given threshold.

        Args:
            red_paths (str or list): Path(s) to red band image(s).
            nir_paths (str or list): Path(s) to near-infrared (NIR) image(s).
            lst_paths (str or list): Path(s) to land surface temperature (LST)
                image(s).
            ndvi_threshold (float): Threshold value for NDVI.
            mode (str): 'above' for NDVI >= threshold, 'below' for NDVI <
                threshold.

        Returns:
            float: Mean of LST values over selected NDVI regions across all
                image sets. Returns np.nan if no valid pixels found.
        """
        import numpy as np
        import rasterio

        if isinstance(red_paths, str):
            red_paths = [red_paths]
        if isinstance(nir_paths, str):
            nir_paths = [nir_paths]
        if isinstance(lst_paths, str):
            lst_paths = [lst_paths]
        if not len(red_paths) == len(nir_paths) == len(lst_paths):
            raise ValueError(
                'red_paths, nir_paths, and lst_paths must '
                'have the same length.'
            )
        all_selected_lst = []
        for red_path, nir_path, lst_path in zip(
            red_paths, nir_paths, lst_paths
        ):
            try:
                with (
                    rasterio.open(red_path) as red_src,
                    rasterio.open(nir_path) as nir_src,
                    rasterio.open(lst_path) as lst_src,
                ):
                    red = red_src.read(1).astype('float32')
                    nir = nir_src.read(1).astype('float32')
                    lst = lst_src.read(1).astype('float32')
                    ndvi_denominator = nir + red
                    ndvi_denominator[ndvi_denominator == 0] = np.nan
                    ndvi = (nir - red) / ndvi_denominator
                    if mode == 'below':
                        mask = (ndvi < ndvi_threshold) & np.isfinite(lst)
                    else:
                        mask = (ndvi >= ndvi_threshold) & np.isfinite(lst)
                    selected_lst = lst[mask]
                    if selected_lst.size > 0:
                        all_selected_lst.append(selected_lst)
            except Exception as e:
                logger.info(
                    f'Error processing {red_path}, {nir_path}, {lst_path}: {e}'
                )
                continue
        if not all_selected_lst:
            return float('nan')
        combined_lst_values = np.concatenate(all_selected_lst)
        return float(np.nanmean(combined_lst_values))

    def calculate_max_lst_by_ndvi(
        self, red_path, nir_path, lst_path, ndvi_threshold, mode='above'
    ):
        """
        Calculate the maximum Land Surface Temperature (LST) in areas where
        NDVI is above or below a given threshold.

        Args:
            red_path (str): Path to the red band image.
            nir_path (str): Path to the near-infrared (NIR) band image.
            lst_path (str): Path to the land surface temperature (LST) image.
            ndvi_threshold (float): Threshold value for NDVI.
            mode (str): 'above' to select NDVI >= threshold, 'below' for NDVI
                < threshold. Default is 'above'.

        Returns:
            float: Maximum LST value over the selected NDVI region. Returns np.
                nan if no valid data.
        """
        import numpy as np
        import rasterio

        with (
            rasterio.open(red_path) as red_src,
            rasterio.open(nir_path) as nir_src,
            rasterio.open(lst_path) as lst_src,
        ):
            red = red_src.read(1).astype('float32')
            nir = nir_src.read(1).astype('float32')
            lst = lst_src.read(1).astype('float32')
            ndvi_denominator = nir + red
            ndvi_denominator[ndvi_denominator == 0] = np.nan
            ndvi = (nir - red) / ndvi_denominator
            if mode == 'below':
                mask = ndvi < ndvi_threshold
            else:
                mask = ndvi >= ndvi_threshold
            selected_lst = lst[mask]
            max_lst = np.nanmax(selected_lst)
            return float(max_lst)

    def calculate_ATI(
        self,
        day_temp_path: str,
        night_temp_path: str,
        albedo_path: str,
        output_path: str,
    ) -> str:
        """
        Description:
            Estimate Apparent Thermal Inertia (ATI) using the Thermal Inertia
            Method.
            ATI is computed as (1 - Albedo) / (Daytime BT - Nighttime BT) and
            serves as a proxy for
            land surface heat retention and thermal stability over diurnal
            cycles.
            The function aligns all raster layers to the daytime brightness
            temperature raster's resolution and extent before calculation.

        Args:
            day_temp_path (str): Path to the daytime brightness temperature
                (BT) GeoTIFF.
            night_temp_path (str): Path to the nighttime brightness
                temperature (BT) GeoTIFF.
            albedo_path (str): Path to the surface albedo GeoTIFF.
            output_path (str): Relative path to save the ATI raster, e.g.
                "question17/thermal_inertia_2022-01-16.tif".

        Return:
            str: Path to the saved Apparent Thermal Inertia GeoTIFF file.

        Example:
            >>> ATI(
            ...     day_temp_path="data/day_temp.tif",
            ...     night_temp_path="data/night_temp.tif",
            ...     albedo_path="data/albedo.tif",
            ...     output_path="question17/thermal_inertia_2022-01-16.tif"
            ... )
            'Result saved at question17/thermal_inertia_2022-01-16.tif'
        """

        import numpy as np
        import rasterio
        from osgeo import gdal

        def resample_to_reference(
            src_data: np.ndarray, src_profile: dict, ref_profile: dict
        ) -> np.ndarray:
            """
            Description:
                Resample a raster array to match the resolution and extent of
                a reference raster profile using GDAL bilinear resampling.

            Args:
                src_data (np.ndarray): Source raster data to be resampled.
                src_profile (dict): Metadata profile of the source raster.
                ref_profile (dict): Metadata profile of the reference raster.

            Return:
                np.ndarray: Resampled raster data array.
            """
            temp_src = 'temp_src.tif'
            temp_dst = 'temp_dst.tif'
            try:
                driver = gdal.GetDriverByName('GTiff')
                dataset = driver.Create(
                    temp_src,
                    src_profile['width'],
                    src_profile['height'],
                    1,
                    gdal.GDT_Float32,
                )
                transform = src_profile['transform']
                geotransform = [
                    transform[2],
                    transform[0],
                    transform[1],
                    transform[5],
                    transform[3],
                    transform[4],
                ]
                dataset.SetGeoTransform(geotransform)
                if src_profile.get('crs'):
                    dataset.SetProjection(src_profile['crs'].to_wkt())
                else:
                    dataset.SetProjection('EPSG:4326')
                dataset.GetRasterBand(1).WriteArray(src_data)
                dataset = None
                gdal.Warp(
                    temp_dst,
                    temp_src,
                    width=ref_profile['width'],
                    height=ref_profile['height'],
                    resampleAlg=gdal.GRA_Bilinear,
                )
                dataset = gdal.Open(temp_dst)
                resampled_data = dataset.GetRasterBand(1).ReadAsArray()
                dataset = None
                return resampled_data
            finally:
                if os.path.exists(temp_src):
                    os.remove(temp_src)
                if os.path.exists(temp_dst):
                    os.remove(temp_dst)

        with rasterio.open(day_temp_path) as src_day:
            BT_day = src_day.read(1).astype(np.float32)
            day_profile = src_day.profile
        with rasterio.open(night_temp_path) as src_night:
            BT_night = src_night.read(1).astype(np.float32)
            night_profile = src_night.profile
        with rasterio.open(albedo_path) as src_alb:
            albedo = src_alb.read(1).astype(np.float32)
            albedo_profile = src_alb.profile
        BT_night = resample_to_reference(BT_night, night_profile, day_profile)
        albedo = resample_to_reference(albedo, albedo_profile, day_profile)
        delta_T = BT_day - BT_night
        delta_T = np.where(delta_T == 0, np.nan, delta_T)
        ATI = (1 - albedo) / delta_T
        ATI = np.clip(ATI, 0, 10)
        day_profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        out_path = Path(TEMP_DIR) / output_path
        os.makedirs(out_path.parent, exist_ok=True)
        with rasterio.open(out_path, 'w', **day_profile) as dst:
            dst.write(ATI, 1)
        return f'Result saved at {out_path}'

    def dual_polarization_differential(
        self,
        pol1_path: str,
        pol2_path: str,
        parameter: str,
        output_path: str,
        a: float = 0.3,
        b: float = 0.1,
        input_unit: str = 'dB',
    ) -> str:
        """
        Dual-Polarization Differential Method (DPDM) for microwave remote
        sensing parameter inversion.

        Supports soil moisture and vegetation index estimation with improved
        data handling and flexible Args.

        Args:
            pol1_path (str): File path for the first polarization band GeoTIFF
                (e.g., VV).
            pol2_path (str): File path for the second polarization band
                GeoTIFF (e.g., VH).
            parameter (str): Parameter to invert, options: "soil_moisture" or
                "vegetation_index".
            output_path (str): relative path for the output raster file, e.g.
                "question17/thermal_inertia_2022-01-16.tif"
            a (float, optional): Linear coefficient for soil moisture model.
                Default is 0.3.
            b (float, optional): Intercept for soil moisture model. Default is
                0.1.
            input_unit (str, optional): Unit of input data, either "dB" or
                "linear". Default is "dB".

        Returns:
            str: Path to the exported parameter GeoTIFF.
        """

        import numpy as np
        import rasterio

        def db2linear(db):
            """Convert decibel (dB) values to linear scale."""
            return 10 ** (db / 10)

        with (
            rasterio.open(pol1_path) as src1,
            rasterio.open(pol2_path) as src2,
        ):
            band1 = src1.read(1).astype(np.float32)
            band2 = src2.read(1).astype(np.float32)
            profile = src1.profile
        if input_unit.lower() == 'db':
            band1 = db2linear(band1)
            band2 = db2linear(band2)
        valid_mask = (band1 > 0) & (band2 > 0)
        output = np.full(band1.shape, np.nan, dtype=np.float32)
        diff = band1 - band2
        sum_ = band1 + band2
        sum_[sum_ == 0] = np.nan
        param_lower = parameter.lower()
        if param_lower == 'soil_moisture':
            output[valid_mask] = a * diff[valid_mask] + b
        elif param_lower == 'vegetation_index':
            output[valid_mask] = diff[valid_mask] / sum_[valid_mask]
        else:
            raise ValueError(
                "Unsupported parameter. "
                "Choose 'soil_moisture' or 'vegetation_index'."
            )
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(output, 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def dual_frequency_diff(
        self,
        band1_path: str,
        band2_path: str,
        parameter: str,
        alpha: float,
        beta: float,
        output_path: str,
    ) -> str:
        r"""Dual-frequency Differential Method (DDM) for parameter inversion.

        Uses local raster data for parameter inversion via empirical linear
        models:

        - Soil Moisture (SM): param = alpha*(band1 - band2) + beta
        - Vegetation Index (VI): param = alpha*(band1 - band2) + beta
        - Leaf Area Index (LAI): param = alpha*(band1 - band2) + beta

        Args:
            band1_path (str): File path for frequency 1 polarization band
                GeoTIFF.
            band2_path (str): File path for frequency 2 polarization band
                GeoTIFF.
            parameter (str): Parameter to invert. Options: 'SM', 'VI', 'LAI'.
                Default is 'SM'.
            alpha (float, optional): Slope coefficient to override default.
            beta (float, optional): Intercept coefficient to override default.
            output_path (str): Relative path for the output raster file,
                e.g. "question17/thermal_inertia_2022-01-16.tif"

        Returns:
            str: Path to the saved combined output GeoTIFF (difference and
                parameter).
        """
        import numpy as np
        import rasterio

        param_models = {
            'SM': {'alpha': 0.7, 'beta': 0.1},
            'VI': {'alpha': 0.5, 'beta': 0.0},
            'LAI': {'alpha': 0.6, 'beta': 0.05},
        }
        parameter_upper = parameter.upper()
        if parameter_upper not in param_models:
            raise ValueError(
                f"Unsupported parameter '{parameter}'. "
                f"Choose from {list(param_models.keys())}"
            )
        alpha_val = (
            alpha
            if alpha is not None
            else param_models[parameter_upper]['alpha']
        )
        beta_val = (
            beta if beta is not None else param_models[parameter_upper]['beta']
        )
        with (
            rasterio.open(band1_path) as src1,
            rasterio.open(band2_path) as src2,
        ):
            band1 = src1.read(1).astype(np.float32)
            band2 = src2.read(1).astype(np.float32)
            profile = src1.profile
            nodata1 = src1.nodata
            nodata2 = src2.nodata
        mask = np.ones_like(band1, dtype=bool)
        if nodata1 is not None:
            mask &= band1 != nodata1
        if nodata2 is not None:
            mask &= band2 != nodata2
        diff = np.full_like(band1, np.nan, dtype=np.float32)
        diff[mask] = band1[mask] - band2[mask]
        param_img = np.full_like(band1, np.nan, dtype=np.float32)
        param_img[mask] = alpha_val * diff[mask] + beta_val
        param_img = np.clip(param_img, 0, 1)
        profile.update(dtype=rasterio.float32, count=2, compress='lzw')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(diff, 1)
            dst.write(param_img, 2)
        return f'Result saved at {TEMP_DIR / output_path}'

    def multi_freq_bt(
        self,
        bt_paths: list[str],
        diff_pairs: list[list[int]],
        parameter: str,
        output_path: str,
    ) -> str:
        """Multi-frequency Brightness Temperature Method for inversion.

        Uses local raster data for parameter inversion.

        Args:
            bt_paths (list[str]): List of local file paths for brightness
                temperature GeoTIFF bands (e.g., ["BT_10GHz.tif",
                "BT_19GHz.tif", "BT_37GHz.tif"]).
            diff_pairs (list[list[int]]): List of index pairs from bt_paths
                for difference calculation (e.g., [[0,1],[1,2]]).
            parameter (str): Parameter to invert. Options: 'SM', 'VWC', 'LAI'.
            output_path (str): Relative path for the output raster file,
                e.g. "question17/thermal_inertia_2022-01-16.tif"

        Returns:
            str: Path to the saved inverted parameter GeoTIFF.
        """
        import numpy as np
        import rasterio

        param_models = {
            'SM': {'alpha': [0.6, 0.4], 'beta': 0.05},
            'VWC': {'alpha': [0.5, 0.5], 'beta': 0.1},
            'LAI': {'alpha': [0.7, 0.3], 'beta': 0.0},
        }
        param_key = parameter.upper()
        if param_key not in param_models:
            raise ValueError(
                f"Unsupported parameter '{parameter}'. "
                f"Choose from {list(param_models.keys())}"
            )
        model = param_models[param_key]
        alpha_list = cast(list[float], model['alpha'])
        beta = model['beta']
        diff_pairs_list = list(diff_pairs)
        if len(alpha_list) != len(diff_pairs_list):
            raise ValueError(
                f'Length of alpha coefficients ({len(alpha_list)}) must match '
                f'number of diff pairs ({len(diff_pairs_list)})'
            )
        bt_arrays = []
        profile = None
        mask = None
        for path in bt_paths:
            with rasterio.open(path) as src:
                band = src.read(1).astype(np.float32)
                if src.nodata is not None:
                    band_mask = band != src.nodata
                else:
                    band_mask = np.ones_like(band, dtype=bool)
                mask = band_mask if mask is None else mask & band_mask
                bt_arrays.append(band)
                if profile is None:
                    profile = src.profile
        n_bands = len(bt_arrays)
        for idx1, idx2 in diff_pairs:
            if idx1 < 0 or idx1 >= n_bands or idx2 < 0 or idx2 >= n_bands:
                raise IndexError(
                    f'diff_pairs contains invalid band index: ({idx1},{idx2})'
                )
        diff_images = []
        for idx1, idx2 in diff_pairs_list:
            diff = bt_arrays[idx1] - bt_arrays[idx2]
            diff_images.append(diff)
        param_img = np.full_like(diff_images[0], beta, dtype=np.float32)
        for alpha, diff in zip(alpha_list, diff_images):
            param_img += alpha * diff
        if mask is None:
            raise RuntimeError('Failed to compute mask from input bands')
        param_img = np.where(mask, param_img, np.nan)
        param_img = np.clip(param_img, 0, 1)
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        if profile is None:
            raise RuntimeError('Failed to read profile from input bands')
        profile.update(
            dtype=rasterio.float32, count=1, compress='lzw', nodata=np.nan
        )
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(param_img.astype(np.float32), 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def chang_single_param_inversion(
        self,
        bt_paths: list[str],
        diff_pairs: list[list[int]],
        parameter: str,
        output_path: str,
    ) -> str:
        """Chang algorithm for single parameter inversion.

        Uses multi-frequency dual-polarized microwave brightness temperatures
        from local raster files.

        Args:
            bt_paths (list[str]): List of local GeoTIFF file paths for
                brightness temperature bands (e.g., ["BT_10V.tif",
                "BT_10H.tif", "BT_19V.tif", "BT_19H.tif"]).
            diff_pairs (list[list[int]]): List of index pairs for brightness
                temperature differences.
            parameter (str): Parameter to invert (e.g., "SM", "VWC").
            output_path (str): Relative path for the output raster file,
                e.g. "question17/thermal_inertia_2022-01-16.tif"

        Returns:
            str: File path to saved GeoTIFF with inverted parameter band.
        """
        import numpy as np
        import rasterio

        parameter = parameter.upper()
        param_models = {
            'SM': {'alpha': [0.65, 0.3, 0.1], 'beta': 0.02},
            'VWC': {'alpha': [0.5, 0.4, 0.2], 'beta': 0.05},
        }
        if parameter not in param_models:
            raise ValueError(
                f"Unsupported parameter '{parameter}'. "
                f"Supported: {list(param_models.keys())}"
            )
        model = param_models[parameter]
        alpha_list = cast(list[float], model['alpha'])
        beta = model['beta']
        diff_pairs_list = list(diff_pairs)
        if len(alpha_list) != len(diff_pairs_list):
            raise ValueError(
                f"Length of alpha coefficients ({len(alpha_list)}) must equal "
                f"number of diff_pairs ({len(diff_pairs_list)}) for parameter "
                f"'{parameter}'"
            )
        bt_arrays = []
        mask = None
        profile = None
        for path in bt_paths:
            with rasterio.open(path) as src:
                band = src.read(1).astype(np.float32)
                nodata = src.nodata
                valid_mask = (
                    band != nodata
                    if nodata is not None
                    else np.ones_like(band, dtype=bool)
                )
                mask = valid_mask if mask is None else mask & valid_mask
                bt_arrays.append(band)
                if profile is None:
                    profile = src.profile
        n_bands = len(bt_arrays)
        for idx1, idx2 in diff_pairs_list:
            if not 0 <= idx1 < n_bands or not 0 <= idx2 < n_bands:
                raise IndexError(
                    f'diff_pairs indices ({idx1},{idx2}) out of range for '
                    f'available bands (0-{n_bands - 1})'
                )
        diff_imgs = []
        for idx1, idx2 in diff_pairs_list:
            diff_imgs.append(bt_arrays[idx1] - bt_arrays[idx2])
        param_img = np.full_like(diff_imgs[0], beta, dtype=np.float32)
        for alpha, diff in zip(alpha_list, diff_imgs):
            param_img += alpha * diff
        if mask is None:
            raise RuntimeError('Failed to compute mask from input bands')
        param_img = np.where(mask, param_img, np.nan)
        param_img = np.clip(param_img, 0, 1)
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        if profile is None:
            raise RuntimeError('Failed to read profile from input bands')
        profile.update(
            dtype=rasterio.float32, count=1, compress='lzw', nodata=np.nan
        )
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(param_img.astype(np.float32), 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def nasa_team_sea_ice_concentration(
        self,
        bt_paths: dict,
        output_path: str,
        nd_ice: float = 50.0,
        nd_water: float = 0.0,
        s1_ice: float = 20.0,
        s1_water: float = 0.0,
    ) -> str:
        """Estimate Sea Ice Concentration using NASA Team Algorithm.

        Uses local passive microwave brightness temperature GeoTIFF files.

        Args:
            bt_paths (dict): Dictionary of local GeoTIFF file paths for
                required brightness temperature bands, e.g.,
                {"19V": "BT_19V.tif", "19H": "BT_19H.tif",
                 "37V": "BT_37V.tif", "37H": "BT_37H.tif"}
            nd_ice (float): ND value for ice reference. Default 50.0.
            nd_water (float): ND value for water reference. Default 0.0.
            s1_ice (float): S1 value for ice reference. Default 20.0.
            s1_water (float): S1 value for water reference. Default 0.0.
            output_path (str): Relative path for the output raster file,
                e.g. "question17/thermal_inertia_2022-01-16.tif"

        Returns:
            str: Path to saved GeoTIFF with sea ice concentration band.
        """
        import numpy as np
        import rasterio

        required_bands = ['19V', '19H', '37V', '37H']
        for band in required_bands:
            if band not in bt_paths:
                raise ValueError(f"Missing required band '{band}' in bt_paths")
        arrays = {}
        profile = None
        try:
            for band in required_bands:
                with rasterio.open(bt_paths[band]) as src:
                    arr = src.read(1).astype(np.float32)
                    if profile is None:
                        profile = src.profile
                    arrays[band] = arr
            valid_mask = np.ones_like(arrays['19V'], dtype=bool)
            for band in required_bands:
                valid_mask &= arrays[band] > 0
            ND = arrays['19V'] - arrays['19H']
            S1 = arrays['37V'] - arrays['37H']
            Ci = np.full_like(ND, np.nan, dtype=np.float32)
            term1 = (ND - nd_water) / (nd_ice - nd_water)
            term2 = (S1 - s1_water) / (s1_ice - s1_water)
            Ci[valid_mask] = (term1[valid_mask] + term2[valid_mask]) / 2
            Ci = np.clip(Ci, 0, 1)
        except Exception as e:
            raise RuntimeError(f'Error processing data: {e}')
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        if profile is None:
            raise RuntimeError('Failed to read profile from input bands')
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
            dst.write(Ci, 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def dual_polarization_ratio(
        self,
        bt_paths: dict,
        parameter: str,
        output_path: str,
        coeffs: (dict | None) = None,
    ) -> str:
        """Estimate VWC or SM using Dual-Polarization Ratio Method (PRM).

        Uses local passive microwave brightness temperature GeoTIFF files.
        The polarization ratio is computed as: (V - H) / (V + H), where V
        and H are brightness temperatures of vertical and horizontal
        polarizations.

        Empirical models:
        - VWC = a_vwc * PR + b_vwc
        - SM  = a_sm * PR + b_sm

        Args:
            bt_paths (dict): Dictionary of local GeoTIFF file paths for
                vertical and horizontal polarization bands, e.g.
                {"V": "BT_V.tif", "H": "BT_H.tif"}
            parameter (str): Parameter to invert, either "VWC" or "SM".
            output_path (str): Relative path for the output raster file,
                e.g. "question17/thermal_inertia_2022-01-16.tif"
            coeffs (dict, optional): Empirical coefficients
                {"VWC": {"a":float, "b":float}, "SM": {...}}.

        Returns:
            str: File path of the saved GeoTIFF containing the inverted
                parameter and PR band.
        """
        import numpy as np
        import rasterio

        if 'V' not in bt_paths or 'H' not in bt_paths:
            raise ValueError("bt_paths dict must contain keys 'V' and 'H'")
        parameter = parameter.upper()
        if coeffs is None:
            coeffs = {'VWC': {'a': 15.0, 'b': 5.0}, 'SM': {'a': 0.4, 'b': 0.1}}
        if parameter not in coeffs:
            raise ValueError(
                f"Unsupported parameter '{parameter}'. "
                f"Supported: {list(coeffs.keys())}"
            )
        try:
            with (
                rasterio.open(bt_paths['V']) as src_v,
                rasterio.open(bt_paths['H']) as src_h,
            ):
                V = src_v.read(1).astype(np.float32)
                H = src_h.read(1).astype(np.float32)
                profile = src_v.profile
            denom = V + H
            denom_safe = np.where(denom == 0, 1e-06, denom)
            pr = (V - H) / denom_safe
            pr = np.clip(pr, -1, 1)
            valid_mask = denom > 1e-06
            param = np.full_like(pr, np.nan, dtype=np.float32)
            a = coeffs[parameter]['a']
            b = coeffs[parameter]['b']
            param[valid_mask] = a * pr[valid_mask] + b
            profile.update(count=2, dtype=rasterio.float32, compress='lzw')
            os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
            with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
                dst.write(param, 1)
                dst.write(pr, 2)
            return f'Result saved at {TEMP_DIR / output_path}'
        except Exception as e:
            raise RuntimeError(
                f'Error processing dual polarization ratio parameter: {e}'
            )

    def calculate_water_turbidity_ntu(
        self,
        input_red_path: str,
        output_path: str,
        method: str = 'linear',
        a: float = 1.0,
        b: float = 0.0,
        n: float = 1.0,
    ) -> str:
        """Calculate water turbidity in NTU from red band raster file.

        NTU = Nephelometric Turbidity Units. Saves result to output path.

        Args:
            input_red_path (str): Path to the Red band raster file.
            output_path (str): Relative path for the output raster file,
                e.g. "benchmark/data/question17/turbidity_2022-01-16.tif"
            method (str): Calculation method - "linear" (a*Red+b),
                "power" (a*Red^n+b), or "log" (a*log(Red)+b).
            a (float): Coefficient parameter, default 1.0.
            b (float): Offset parameter, default 0.0.
            n (float): Power parameter for power method, default 1.0.

        Returns:
            str: Path to the output NTU raster file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_red_path) as red_src:
            red_band = red_src.read(1)
            red_profile = red_src.profile
        red_band = np.array(red_band, dtype=np.float32)
        if method == 'linear':
            ntu = a * red_band + b
        elif method == 'power':
            red_positive = np.maximum(red_band, 1e-06)
            ntu = a * red_positive**n + b
        elif method == 'log':
            red_positive = np.maximum(red_band, 1e-06)
            ntu = a * np.log(red_positive) + b
        else:
            raise ValueError("Method must be 'linear', 'power', or 'log'")
        ntu = np.maximum(ntu, 0)
        ntu_profile = red_profile.copy()
        ntu_profile.update(
            dtype=rasterio.float32, nodata=-9999, compress='lzw'
        )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **ntu_profile) as dst:
            dst.write(ntu.astype(rasterio.float32), 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def threshold_segmentation(self, input_image_path, threshold, output_path):
        """Perform threshold-based segmentation on a single-band raster image.

        Reads a raster image, converts it to a binary mask by applying a fixed
        threshold, and writes the resulting binary image to a new file. Pixel
        values greater than threshold are set to 255 (white), and values less
        than or equal to threshold are set to 0 (black).

        Args:
            input_image_path (str): Path to the input raster image file
                (e.g., TIFF, PNG, JPG).
            threshold (float or int): Pixel intensity threshold used to
                generate the binary mask.
            output_path (str): Relative output path (under TEMP_DIR) where
                the result will be saved, e.g.,
                "question17/threshold_segmentation_2022-01-16.tif".

        Returns:
            str: Message indicating the file path where the result is saved.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_image_path) as src:
            image = src.read(1)
            meta = src.meta.copy()
        binary_image = (image > threshold).astype(np.uint8) * 255
        meta.update(dtype=rasterio.uint8, count=1)
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(TEMP_DIR / output_path, 'w', **meta) as dst:
            dst.write(binary_image, 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def bbox_expansion(
        self, bboxes: list[list[float]], radius: float, gsd: float
    ):
        """Expand bounding boxes by a given radius.

        Args:
            bboxes (list[list[float]]): List of bounding boxes, each
                represented as [x1, y1, x2, y2].
            radius (float): Expansion radius in the same unit as the GSD.
            gsd (float): Ground Sampling Distance in the same unit as radius.

        Returns:
            list[list[float]]: List of expanded bounding boxes, each
                represented as [x1, y1, x2, y2].
        """
        expanded_bboxes = []
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            x1 = x1 - radius / gsd
            y1 = y1 - radius / gsd
            x2 = x2 + radius / gsd
            y2 = y2 + radius / gsd
            expanded_bboxes.append([x1, y1, x2, y2])
        return expanded_bboxes

    def count_above_threshold(self, file_path: str, threshold: float):
        """Count pixels in an image whose values exceed the threshold.

        Args:
            file_path (str):
                Path to the input image (GeoTIFF or raster format).
            threshold (float):
                Threshold value for hotspot detection.

        Returns:
            count (int):
                Number of pixels with values greater than the threshold.

        Example:
            >>> count_above_threshold("sample_image.tif", 100)
            2456
        """
        import numpy as np
        import rasterio

        with rasterio.open(file_path) as src:
            x = src.read(1)
        x = np.asarray(x)
        count = np.sum(x > threshold)
        return int(count)

    def count_skeleton_contours(self, image_path):
        """Count external contours in a skeletonized binary image.

        Reads a binary image, applies erosion and skeletonization, then
        counts the number of external contours.

        Args:
            image_path (str):
                Path to the input binary (black and white) image.

        Returns:
            count (int):
                Number of external contours detected after skeletonization.

        Example:
            >>> count_skeleton_contours("binary_mask.png")
            12
        """
        import cv2
        import numpy as np
        from skimage.morphology import skeletonize

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f'Failed to read image: {image_path}')
        _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3, 3), np.uint8)
        eroded = cv2.erode(binary, kernel, iterations=1)
        skeleton = skeletonize(eroded > 0)
        skeleton_uint8 = (skeleton * 255).astype(np.uint8)
        contours, _ = cv2.findContours(
            skeleton_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        return len(contours)

    def bboxes2centroids(self, bboxes):
        """Convert bounding boxes to centroid coordinates.

        Converts from [x_min, y_min, x_max, y_max] format to (x, y) centroids.

        Args:
            bboxes (list[list[float]]): A list of bounding boxes, each
                defined as [x_min, y_min, x_max, y_max].

        Returns:
            centroids (list[tuple[float, float]]):
                A list of centroid coordinates, each in (x, y) format.

        Example:
            >>> bboxes2centroids([[0, 0, 10, 20], [5, 5, 15, 15]])
            [(5.0, 10.0), (10.0, 10.0)]
        """
        return [((x1 + x2) / 2, (y1 + y2) / 2) for x1, y1, x2, y2 in bboxes]

    def centroid_distance_extremes(self, centroids):
        """Find closest and farthest centroid pairs.

        Computes pairwise distances between centroids and returns both the
        closest and farthest pairs with their indices and distances.

        Args:
            centroids (list[tuple[float, float]] or np.ndarray):
                A list or NumPy array of centroid coordinates in (x, y) format.

        Returns:
            result (dict):
                A dictionary containing:
                - 'min': (index1, index2, distance)
                    Indices of the closest centroid pair and their distance.
                - 'max': (index1, index2, distance)
                    Indices of the farthest centroid pair and their distance.

        Example:
            >>> centroids = [(0, 0), (3, 4), (10, 0)]
            >>> centroid_distance_extremes(centroids)
            {'min': (0, 1, 5.0), 'max': (1, 2, 7.211102550927978)}
        """
        import numpy as np

        points = np.array(centroids)
        diff = points[:, None, :] - points[None, :, :]
        dist_matrix = np.sqrt(np.sum(diff**2, axis=-1))
        np.fill_diagonal(dist_matrix, np.inf)
        min_idx = np.unravel_index(np.argmin(dist_matrix), dist_matrix.shape)
        min_dist = dist_matrix[min_idx]
        np.fill_diagonal(dist_matrix, -np.inf)
        max_idx = np.unravel_index(np.argmax(dist_matrix), dist_matrix.shape)
        max_dist = dist_matrix[max_idx]
        return {
            'min': (int(min_idx[0]), int(min_idx[1]), float(min_dist)),
            'max': (int(max_idx[0]), int(max_idx[1]), float(max_dist)),
        }

    def calculate_bbox_area(self, bboxes, gsd=None):
        """Calculate the total area of bounding boxes in [x, y, w, h] format.

        Args:
            bboxes (list[list[float]]): A list of bounding boxes, each
                defined as [x, y, w, h] where x,y is top-left corner and
                w,h are width and height.
            gsd (float, optional): Ground sample distance (meters per pixel).
                If provided, result is in m². If None, result is in pixel².
                Default = None.

        Returns:
            total_area (float): The total area of all bounding boxes, in m²
                if gsd is provided, otherwise in pixel².

        Example:
            >>> calculate_bbox_area([[0, 0, 10, 20], [5, 5, 15, 10]])
            350.0
            >>> calculate_bbox_area([[0, 0, 10, 20]], gsd=0.5)
            50.0
        """
        total_area = 0.0
        for bbox in bboxes:
            if len(bbox) != 4:
                raise ValueError(
                    f'Invalid bbox format: {bbox}. Expected [x, y, w, h].'
                )
            _, _, w, h = bbox
            area = w * h
            total_area += area
        if gsd is not None:
            total_area *= gsd * gsd
        return total_area

    def compute_linear_trend(self, y: list, x: (list | None) = None):
        r"""Compute linear trend (slope and intercept) of a time series.

        Fits a line of the form y = a * x + b using least squares method.

        Args:
            y (list): The dependent variable (time series data).
            x (list): The independent variable (time indices). If not
                provided, uses np.arange(len(y)) as default.

        Returns:
            tuple: (slope, intercept) where:
                - slope (float): The coefficient a representing the trend.
                  > 0: upward, < 0: downward, ~0: no trend.
                - intercept (float): The y-intercept b of the fitted line.
        """
        import numpy as np

        y_arr = np.asarray(y)
        if x is None:
            x_arr = np.arange(len(y_arr))
        else:
            x_arr = np.asarray(x)
        if len(x_arr) != len(y_arr):
            raise ValueError('len(x) != len(y)')
        A = np.vstack([x_arr, np.ones_like(x_arr)]).T
        a, b = np.linalg.lstsq(A, y_arr, rcond=None)[0]
        return float(a), float(b)

    def mann_kendall_test(self, x: list):
        """
        Description:
            Conduct the Mann-Kendall trend test on a time series to assess
            whether a statistically significant monotonic trend exists.
            The test is non-parametric and does not assume normality.
            Handles tied ranks with variance correction.

        Args:
            x (list[float]):
                The input time series data as a list of floats or ints.
                Any missing values (NaN) should be removed beforehand.

        Returns:
            trend (str):
                Type of detected trend:
                - "increasing" if a significant upward trend is found
                - "decreasing" if a significant downward trend is found
                - "no trend" if no significant trend is detected
            p_value (float):
                Two-tailed p-value of the test.
            z (float):
                Standard normal test statistic.
            tau (float):
                Kendall's Tau statistic (measure of rank correlation,
                range -1 to 1).

        Example:
            >>> mann_kendall_test([1, 2, 3, 4, 5])
            ('increasing', 0.03, 2.12, 0.9)
        """
        import numpy as np
        from scipy.stats import norm

        x_arr = np.asarray(x)
        n = len(x_arr)
        s = 0
        for k in range(n - 1):
            s += np.sum(np.sign(x_arr[k + 1 :] - x_arr[k]))
        _, counts = np.unique(x_arr, return_counts=True)
        if n == len(np.unique(x_arr)):
            var_s = n * (n - 1) * (2 * n + 5) / 18
        else:
            var_s = (
                n * (n - 1) * (2 * n + 5)
                - np.sum(counts * (counts - 1) * (2 * counts + 5))
            ) / 18
        if s > 0:
            z = (s - 1) / np.sqrt(var_s)
        elif s < 0:
            z = (s + 1) / np.sqrt(var_s)
        else:
            z = 0
        p = 2 * (1 - norm.cdf(abs(z)))
        tau = s / (0.5 * n * (n - 1))
        alpha = 0.05
        if p < alpha:
            trend = 'increasing' if z > 0 else 'decreasing'
        else:
            trend = 'no trend'
        return trend, float(p), float(z), float(tau)

    def sens_slope(self, x: list):
        """
        Description:
            Compute Sen's Slope estimator for a univariate time series.
            This robust non-parametric method calculates the median of
            all pairwise slopes between observations, providing an estimate
            of the overall monotonic trend magnitude.

        Args:
            x (list[float]):
                The input time series data as a list of floats or ints.
                Must have at least two data points.

        Returns:
            slope (float):
                The Sen's Slope estimate (median of all pairwise slopes).
            slopes (list[float]):
                List of all pairwise slopes, which can be used for
                further distributional or variability analysis.

        Example:
            >>> sens_slope([2, 4, 6, 8, 10])
            (2.0, [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0])
        """
        import numpy as np

        x_arr = np.asarray(x)
        n = len(x_arr)
        if n < 2:
            raise ValueError('At least two data points are required.')
        slopes_list: list = []
        for i in range(n - 1):
            for j in range(i + 1, n):
                slope_ij = (x_arr[j] - x_arr[i]) / (j - i)
                slopes_list.append(slope_ij)
        slopes_arr = np.array(slopes_list)
        median_slope = np.median(slopes_arr)
        return float(median_slope), [float(s) for s in slopes_arr]

    def stl_decompose(self, x: list, period: int, robust: bool = True):
        """Apply STL decomposition to a univariate time series.

        Decomposes input data into three additive components: trend,
        seasonal, and residual using LOESS.

        Args:
            x (list[float]): Input time series values.
            period (int): Number of observations in one seasonal cycle.
                Example: 12 for monthly data with yearly seasonality.
            robust (bool, default=True): If True, use robust version of STL,
                which is less sensitive to outliers.

        Returns:
            dict: Dictionary with keys "trend", "seasonal", "resid", each
                containing list[float] of component values.

        Example:
            >>> stl_decompose([10, 12, 15, 20, 18, 16], period=12)
            {"trend": [...], "seasonal": [...], "resid": [...]}
        """
        import pandas as pd
        from statsmodels.tsa.seasonal import STL

        if not isinstance(x, pd.Series):
            x = pd.Series(x)
        stl = STL(x, period=period, robust=robust)
        result = stl.fit()
        return {
            'trend': [float(x) for x in result.trend],
            'seasonal': [float(x) for x in result.seasonal],
            'resid': [float(x) for x in result.resid],
        }

    def detect_change_points(self, signal, model='l2', penalty=10):
        """
        Description:
            Detect change points in a one-dimensional time series using the
            PELT algorithm from the ruptures library. This identifies indices
            where the statistical structure of the signal changes.

        Args:
            signal (list[float]):
                Input time series data.
            model (str, default="l2"):
                Segmentation cost model to use.
                - "l1": robust to outliers (absolute loss)
                - "l2": mean shift model (squared loss, default)
                - "rbf": kernel-based model for nonlinear changes
                - others supported by ruptures
            penalty (float, default=10):
                Penalty value controlling sensitivity.
                Higher values detect fewer change points (more conservative).

        Returns:
            change_points (list[int]):
                List of indices marking change points in the series.
                The final index of the signal is always included.

        Example:
            >>> detect_change_points([1, 1, 1, 10, 10, 10], model="l2",
            penalty=5)
            [3, 6]
        """
        import numpy as np
        import ruptures as rpt

        signal = np.asarray(signal)
        algo = rpt.Pelt(model=model).fit(signal)
        change_points = algo.predict(pen=penalty)
        return [int(cp) for cp in change_points]

    def autocorrelation_function(self, x: list, nlags: int = 20):
        """Compute the Autocorrelation Function (ACF) of a time series.

        The ACF describes correlation between the series and its lagged values,
        commonly used to detect seasonality or serial dependence.

        Args:
            x (list[float]): Input time series data.
            nlags (int, default=20): Number of lags to compute.

        Returns:
            acf (list[float]): Autocorrelation values for lags 0 to nlags.
                acf[0] = 1.0 (self-correlation), acf[k] = correlation at lag k.

        Example:
            >>> autocorrelation_function([1, 2, 3, 4, 5], nlags=3)
            [1.0, 0.5, 0.0, -0.5]
        """
        import numpy as np

        x_arr = np.asarray(x)
        x_arr = x_arr - np.mean(x_arr)
        n = len(x_arr)
        acf = np.empty(nlags + 1)
        var = np.dot(x_arr, x_arr) / n
        for lag in range(nlags + 1):
            if lag == 0:
                acf[lag] = 1.0
            else:
                acf[lag] = np.dot(x_arr[:-lag], x_arr[lag:]) / (n - lag) / var
        return [float(val) for val in acf]

    def detect_seasonality_acf(self, values: list, min_acf: float = 0.3):
        """Detect dominant seasonality in a time series using ACF.

        A peak in the ACF beyond lag=1 indicates potential periodicity.

        Args:
            values (list[float]): Input time series data.
            min_acf (float, default=0.3): ACF threshold to consider
                significant.

        Returns:
            result (int | str): Dominant period (lag) if detected, or
                "Data is not cyclical" if no significant seasonality found.

        Example:
            >>> detect_seasonality_acf([1, 2, 1, 2, 1, 2], min_acf=0.3)
            2
            >>> detect_seasonality_acf([1, 2, 3, 4, 5], min_acf=0.3)
            'Data is not cyclical'
        """
        import numpy as np
        from statsmodels.tsa.stattools import acf

        values_arr = np.asarray(values)
        n = len(values_arr)
        nlags = min(n // 3, 40)
        if nlags < 2:
            return 'Data is not cyclical'
        try:
            acf_values = acf(values_arr, nlags=nlags, fft=True)
        except Exception:
            return 'Data is not cyclical'
        max_acf = 0
        best_lag = None
        for lag in range(2, len(acf_values)):
            if acf_values[lag] > max_acf and acf_values[lag] > min_acf:
                max_acf = acf_values[lag]
                best_lag = lag
        if best_lag is None:
            return 'Data is not cyclical'
        else:
            return best_lag

    def getis_ord_gi_star(
        self, image_path: str, weight_matrix: list, output_path: str
    ) -> str:
        """Compute Getis-Ord Gi* statistic for local spatial autocorrelation.

        Positive Gi* values indicate hot spots (clusters of high values),
        negative values indicate cold spots (clusters of low values).

        Args:
            image_path (str): Path to input single-band raster (GeoTIFF).
            weight_matrix (list[list[float]]): 2D spatial weight kernel
                (e.g., 3x3 or 5x5). Sum of weights must not be zero.
            output_path (str): Relative path to save the Gi* result GeoTIFF.

        Returns:
            str: Path to saved GeoTIFF with Gi* statistics (float32 raster).
                Preserves georeference and projection from input if available.

        Example:
            >>> getis_ord_gi_star("ndvi.tif", [[1,1,1],[1,0,1],[1,1,1]], "out.
                tif") 'Result save at out.tif'
        """
        import numpy as np
        from osgeo import gdal
        from scipy.ndimage import convolve

        ds = gdal.Open(image_path)
        if ds is None:
            raise RuntimeError(f'Failed to open image: {image_path}')
        img = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
        img[np.isnan(img)] = 0
        W = np.array(weight_matrix, dtype=np.float64)
        W_sum = np.sum(W)
        if W_sum == 0:
            raise ValueError('Sum of weights must not be zero.')
        x_bar = np.mean(img)
        s = np.std(img)
        n = img.size
        numerator = convolve(img, W, mode='constant', cval=0)
        W_sq_sum = np.sum(W**2)
        denom_part = (n * W_sq_sum - W_sum**2) / (n - 1)
        denominator = s * np.sqrt(denom_part)
        gi_star = (numerator - x_bar * W_sum) / denominator
        (TEMP_DIR / output_path).parent.mkdir(parents=True, exist_ok=True)
        driver = gdal.GetDriverByName('GTiff')
        out_ds = driver.Create(
            str(TEMP_DIR / output_path),
            xsize=gi_star.shape[1],
            ysize=gi_star.shape[0],
            bands=1,
            eType=gdal.GDT_Float32,
        )
        out_ds.GetRasterBand(1).WriteArray(gi_star.astype(np.float32))
        if ds.GetGeoTransform():
            out_ds.SetGeoTransform(ds.GetGeoTransform())
        if ds.GetProjection():
            out_ds.SetProjection(ds.GetProjection())
        out_ds.FlushCache()
        out_ds = None
        return f'Result save at {TEMP_DIR / output_path}'

    def analyze_hotspot_direction(self, hotspot_map_path: str) -> str:
        """Analyze dominant direction of hotspot concentration.

        Computes the relative location of hotspot pixels (value=1) with
        respect to raster center and determines which cardinal direction
        contains the majority of hotspots.

        Args:
            hotspot_map_path (str): Path to binary hotspot map GeoTIFF.
                Hotspot pixels should be value=1; others are ignored.

        Returns:
            str: "north", "south", "east", "west" for dominant direction,
                or "no hotspots found" if no hotspot pixels exist.

        Example:
            >>> analyze_hotspot_direction("outputs/hotspot_map.tif")
            'north'
        """
        import numpy as np
        import rasterio

        with rasterio.open(hotspot_map_path) as src:
            hotspot_data = src.read(1)
        hotspot_indices = np.where(hotspot_data == 1)
        if len(hotspot_indices[0]) == 0:
            return 'no hotspots found'
        center_y = hotspot_data.shape[0] // 2
        center_x = hotspot_data.shape[1] // 2
        directions = {'north': 0, 'south': 0, 'east': 0, 'west': 0}
        for y, x in zip(hotspot_indices[0], hotspot_indices[1]):
            dy = center_y - y
            dx = x - center_x
            if abs(dy) > abs(dx):
                if dy > 0:
                    directions['north'] += 1
                else:
                    directions['south'] += 1
            elif dx > 0:
                directions['east'] += 1
            else:
                directions['west'] += 1
        max_direction = max(directions.keys(), key=lambda x: directions[x])
        return max_direction

    def count_spikes_from_values(
        self, values, spike_threshold=0.1, verbose=True
    ):
        """
        Count the number of upward spikes in a sequence of numerical values.

        A spike is defined as a positive difference between consecutive valid
        values greater than the given threshold.

        Args:
            values (list of float):
                Input sequence of values (can include None or NaN).
            spike_threshold (float):
                Minimum positive change required to count as a spike.
            verbose (bool):
                If True, logger.infos details for each detected spike.

        Returns:
            int:
                Number of detected upward spikes.

        Example:
            >>> count_spikes_from_values([0.1, 0.15, 0.5], spike_threshold=0.2)
            1
        """
        import numpy as np

        values = np.array(values, dtype=np.float32)
        valid_indices = ~np.isnan(values)
        valid_values = values[valid_indices]
        if len(valid_values) < 2:
            if verbose:
                logger.info(
                    'Warning: Insufficient valid data for spike analysis'
                )
            return 0
        spike_count = 0
        for i in range(1, len(valid_values)):
            diff = valid_values[i] - valid_values[i - 1]
            if diff > spike_threshold:
                spike_count += 1
                if verbose:
                    logger.info(
                        f'Spike detected: {valid_values[i - 1]:.4f} -> '
                        f'{valid_values[i]:.4f}, Δ = {diff:.4f}'
                    )
        if verbose:
            logger.info(f'\nTotal number of spikes detected: {spike_count}')
        return spike_count

    def coefficient_of_variation(self, x: list, ddof: int = 1):
        """
        Description:
            Compute the Coefficient of Variation (CV) for a dataset.
            CV is defined as the ratio of the standard deviation to the mean:
                CV = std(x) / mean(x)

        Args:
            x (list[float]):
                Input dataset values (numeric).
            ddof (int, default=1):
                Delta Degrees of Freedom for standard deviation calculation:
                - ddof=0 → population standard deviation
                - ddof=1 → sample standard deviation (default)

        Returns:
            cv (float):
                The computed Coefficient of Variation.
                Returns NaN if mean(x) == 0 to avoid division by zero.

        Example:
            >>> coefficient_of_variation([10, 12, 8, 9, 11])
            0.14586499149789456
        """
        import numpy as np

        x_arr = np.asarray(x)
        mean = np.mean(x_arr)
        std = np.std(x_arr, ddof=ddof)
        if mean == 0:
            return float('nan')
        return float(std / mean)

    def skewness(self, x: list, bias: bool = True):
        """Compute skewness of a dataset (distribution asymmetry).

        Positive skew = longer right tail, negative = longer left tail,
        zero = approximately symmetric.

        Args:
            x (list[float]): Input dataset values (numeric).
            bias (bool, default=True): If False, applies bias correction
                (Fisher-Pearson method) for unbiased estimator.

        Returns:
            skew (float): Skewness value. Returns 0.0 if no variation.

        Example:
            >>> skewness([1, 2, 3, 4, 5])
            0.0
            >>> skewness([1, 1, 2, 5, 10])
            1.446915
        """
        import numpy as np

        x_arr = np.asarray(x)
        n = len(x_arr)
        mean = np.mean(x_arr)
        std = np.std(x_arr, ddof=0 if bias else 1)
        if std == 0:
            return 0.0
        m3 = np.mean((x_arr - mean) ** 3)
        skew = m3 / std**3
        if not bias and n > 2:
            skew *= np.sqrt(n * (n - 1)) / (n - 2)
        return float(skew)

    def kurtosis(self, x: list, bias: bool = True, fisher: bool = True):
        """Compute kurtosis of a dataset (tailedness measure).

        Positive kurtosis = heavier tails than normal, negative = lighter.
        Zero kurtosis = similar tails to normal (when fisher=True).

        Args:
            x (list[float]): Input dataset values (numeric).
            bias (bool, default=True): If False, applies bias correction.
            fisher (bool, default=True): If True, returns "excess kurtosis"
                (normal=0). If False, returns regular kurtosis (normal=3).

        Returns:
            kurt (float): Kurtosis value. Returns 0.0 if no variation.

        Example:
            >>> kurtosis([1, 2, 3, 4, 5])
            -1.3
            >>> kurtosis([10, 10, 10, 10])
            0.0
            >>> kurtosis([1, 2, 2, 2, 100], fisher=False)
            5.12
        """
        import numpy as np

        x_arr = np.asarray(x)
        n = len(x_arr)
        mean = np.mean(x_arr)
        std = np.std(x_arr, ddof=0 if bias else 1)
        if std == 0:
            return 0.0
        m4 = np.mean((x_arr - mean) ** 4)
        kurt = m4 / std**4
        if not bias and n > 3:
            numerator = n * (n + 1) * ((x_arr - mean) ** 4).sum()
            denominator = (n - 1) * (n - 2) * (n - 3) * std**4
            adjustment = numerator / denominator
            excess = 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
            kurt = adjustment - excess
        if fisher:
            kurt -= 3
        return float(kurt)

    def calc_single_image_mean(
        self, file_path: str, uint8: bool = False
    ) -> float:
        """
        Compute mean value of an image.

        Args:
            file_path (str): Path to input image.

        Returns:
            mean (float): Mean pixel value
        """
        import numpy as np

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        return float(np.nanmean(flat))

    def calc_batch_image_mean(
        self, file_list: list[str], uint8: bool = False
    ) -> list[float]:
        """
        Compute mean value of an batch of images.

        Args:
            file_list (list(str)): Paths to input images.

        Returns:
            mean (list(float)): Mean pixel value
        """
        return [
            float(self.calc_single_image_mean(file_path, uint8))
            for file_path in file_list
        ]

    def calc_single_image_std(
        self, file_path: str, uint8: bool = False
    ) -> float:
        """
        Compute standard deviation value of an image.

        Args:
            file_path (str): Path to input image.

        Returns:
            std (float): Standard deviation
        """
        import numpy as np

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        return float(np.nanstd(flat, ddof=1))

    def calc_batch_image_std(
        self, file_list: list[str], uint8: bool = False
    ) -> list[float]:
        """Compute standard deviation for a batch of images.

        Args:
            file_list (list[str]): List of input image file paths.
            uint8 (bool, optional): Whether to convert to uint8 first.
                Default = False.

        Returns:
            list[float]: Standard deviation values, one per input image.
        """
        return [
            float(self.calc_single_image_std(file_path, uint8))
            for file_path in file_list
        ]

    def calc_single_image_median(
        self, file_path: str, uint8: bool = False
    ) -> float:
        """
        Compute median value of an image.

        Args:
            file_path (str): Path to input image.

        Returns:
            median (float): Median pixel value
        """
        import numpy as np

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        return float(np.nanmedian(flat))

    def calc_batch_image_median(
        self, file_list: list[str], uint8: bool = False
    ) -> list[float]:
        """Compute median pixel value for a batch of images.

        Args:
            file_list (list[str]): List of input image file paths.
            uint8 (bool, optional): Whether to convert to uint8 first.
                Default = False.

        Returns:
            list[float]: Median pixel values, one per input image.
        """
        return [
            float(self.calc_single_image_median(file_path, uint8))
            for file_path in file_list
        ]

    def calc_single_image_min(
        self, file_path: str, uint8: bool = False
    ) -> float:
        """
        Compute min value of an image.

        Args:
            file_path (str): Path to input image.

        Returns:
            min (float): Minimum pixel value
        """
        import numpy as np

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        return float(np.nanmin(flat))

    def calc_batch_image_min(
        self, file_list: list[str], uint8: bool = False
    ) -> list[float]:
        """Compute minimum pixel value for a batch of images.

        Args:
            file_list (list[str]): List of input image file paths.
            uint8 (bool, optional): Whether to convert to uint8 first.
                Default = False.

        Returns:
            list[float]: Minimum pixel values, one per input image.
        """
        return [
            float(self.calc_single_image_min(file_path, uint8))
            for file_path in file_list
        ]

    def calc_single_image_max(
        self, file_path: str, uint8: bool = False
    ) -> float:
        """
        Compute max value of an image.

        Args:
            file_path (str): Path to input image.

        Returns:
            max (float): Maximum pixel value
        """
        import numpy as np

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        return float(np.nanmax(flat))

    def calc_batch_image_max(
        self, file_list: list[str], uint8: bool = False
    ) -> list[float]:
        """Compute maximum pixel value for a batch of images.

        Args:
            file_list (list[str]): List of input image file paths.
            uint8 (bool, optional): Whether to convert to uint8 first.
                Default = False.

        Returns:
            list[float]: Maximum pixel values, one per input image.
        """
        return [
            float(self.calc_single_image_max(file_path, uint8))
            for file_path in file_list
        ]

    def calc_single_image_skewness(
        self, file_path: str, uint8: bool = False
    ) -> float:
        """
        Compute skewness value of an image.

        Args:
            file_path (str): Path to input image.

        Returns:
            skewness: Skewness of pixel value distribution
        """
        import numpy as np
        from scipy.stats import skew

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        return float(skew(flat, bias=False))

    def calc_batch_image_skewness(
        self, file_list: list[str], uint8: bool = False
    ) -> list[float]:
        """Compute skewness of pixel distributions for a batch of images.

        Positive skew = longer right tail, negative = longer left tail,
        zero = symmetric distribution.

        Args:
            file_list (list[str]): List of input image file paths.
            uint8 (bool, optional): Whether to convert to uint8 first.
                Default = False.

        Returns:
            list[float]: Skewness values, one per input image.
        """
        return [
            float(self.calc_single_image_skewness(file_path, uint8))
            for file_path in file_list
        ]

    def calc_single_image_kurtosis(
        self, file_path: str, uint8: bool = False
    ) -> float:
        """
        Compute kurtosis value of an image.

        Args:
            file_path (str): Path to input image.

        Returns:
            kurtosis: Kurtosis of pixel value distribution (excess kurtosis)
        """
        import numpy as np
        from scipy.stats import kurtosis

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        flat_clean = flat[~np.isnan(flat)]
        if len(flat_clean) == 0:
            raise ValueError('No valid data points for kurtosis calculation')
        return float(kurtosis(flat_clean, fisher=False))

    def calc_batch_image_kurtosis(
        self, file_list: list[str], uint8: bool = False
    ) -> list[float]:
        """Compute kurtosis of pixel distributions for a batch of images.

        Kurtosis measures "tailedness" relative to normal distribution.
        Normal = 3, higher = heavier tails, lower = lighter tails.

        Args:
            file_list (list[str]): List of input image file paths.
            uint8 (bool, optional): Whether to convert to uint8 first.
                Default = False.

        Returns:
            list[float]: Kurtosis values, one per input image.
        """
        return [
            float(self.calc_single_image_kurtosis(file_path, uint8))
            for file_path in file_list
        ]

    def calc_single_image_sum(
        self, file_path: str, uint8: bool = False
    ) -> float:
        """
        Compute sum value of an image.

        Args:
            file_path (str): Path to input image.
            uint8 (bool): Whether to use uint8 format.

        Returns:
            sum (float): Sum pixel value
        """
        import numpy as np

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        return float(np.nansum(flat))

    def calc_batch_image_sum(
        self, file_list: list[str], uint8: bool = False
    ) -> list[float]:
        """
        Description:
        Compute the sum of pixel values for a batch of images.

        Args:
        - file_list (list[str]): List of input image file paths.
        - uint8 (bool, optional): Whether to convert images to uint8 format
            before computation. Default = False.

        Returns:
        - sum (list[float]): List of pixel sum values, one for each image.
        """
        return [
            float(self.calc_single_image_sum(file_path, uint8))
            for file_path in file_list
        ]

    def calc_single_image_hotspot_percentage(
        self, file_path: str, threshold: float, uint8: bool = False
    ) -> float:
        """
        Compute hotspot percentage of an image.

        Args:
            file_path (str): Path to input image.
            threshold (float): Threshold value for hotspot detection.
            uint8 (bool): Whether to use uint8 format.

        Returns:
            percentage (float): Hotspot area percentage (0.0 to 1.0).
        """
        import numpy as np

        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        flat = img.flatten()
        flat = np.where(np.isinf(flat), np.nan, flat)
        valid_pixels = flat[~np.isnan(flat)]
        if len(valid_pixels) == 0:
            return 0.0
        hotspot_pixels = valid_pixels[valid_pixels > threshold]
        hotspot_percentage = len(hotspot_pixels) / len(valid_pixels)
        return float(hotspot_percentage)

    def calc_batch_image_hotspot_percentage(
        self, file_list: list[str], threshold: float, uint8: bool = False
    ) -> list[float]:
        """
        Description:
        Compute the hotspot percentage (fraction of pixels above a threshold)
        for a batch of images.

        Args:
        - file_list (list[str]): List of input image file paths.
        - threshold (float): Threshold value for hotspot detection. Pixels with
            values greater than this threshold are counted as hotspots.
        - uint8 (bool, optional): Whether to convert images to uint8 format
            before computation. Default = False.

        Returns:
        - percentage (list[float]): List of hotspot area percentages (0.0-1.0),
            one for each input image.
        """
        return [
            float(
                self.calc_single_image_hotspot_percentage(
                    file_path, threshold, uint8
                )
            )
            for file_path in file_list
        ]

    def calc_single_image_hotspot_tif(
        self,
        file_path: str,
        threshold: float,
        output_path: str,
        uint8: bool = False,
    ) -> str:
        """
        Create a binary map highlighting areas below the threshold and save
        as GeoTIFF.

        Args:
            file_path (str): Path to input image.
            threshold (float): Threshold value for detection.
            uint8 (bool): Whether to use uint8 format.
            output_path (str, optional): relative path for the output raster
                file, e.g. "question17/hotspot_2022-01-16.tif"

        Returns:
            str: Path to the saved GeoTIFF image containing the binary map.
        """
        import numpy as np
        from osgeo import gdal

        ds = gdal.Open(file_path)
        if ds is None:
            raise RuntimeError(f'Failed to open image: {file_path}')
        if uint8:
            img = self.read_image_uint8(file_path)
        else:
            img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        img = np.where(np.isinf(img), np.nan, img)
        mask = np.zeros_like(img, dtype=np.float32)
        mask[img < threshold] = 1.0
        mask[img >= threshold] = 0.0
        mask[np.isnan(img)] = np.nan
        output_path_full = TEMP_DIR / output_path
        os.makedirs(output_path_full.parent, exist_ok=True)
        driver = gdal.GetDriverByName('GTiff')
        out_ds = driver.Create(
            str(output_path_full),
            xsize=mask.shape[1],
            ysize=mask.shape[0],
            bands=1,
            eType=gdal.GDT_Float32,
        )
        out_ds.GetRasterBand(1).WriteArray(mask)
        out_ds.GetRasterBand(1).SetNoDataValue(np.nan)
        if ds.GetGeoTransform():
            out_ds.SetGeoTransform(ds.GetGeoTransform())
        if ds.GetProjection():
            out_ds.SetProjection(ds.GetProjection())
        out_ds.FlushCache()
        out_ds = None
        ds = None
        return f'Result save at {output_path_full}'

    def calc_batch_image_hotspot_tif(
        self,
        file_list: list[str],
        threshold: float,
        output_path_list: list[str],
        uint8: bool = False,
    ) -> list[str]:
        """
        Description:
        Create binary hotspot maps for a batch of images, where pixels below
        a specified threshold are set to 1 (hotspot) and others set to 0.
        The output is saved as GeoTIFF files, preserving georeference metadata
        from the input images.

        Args:
        - file_list (list[str]): List of input image file paths.
        - threshold (float): Threshold value for hotspot detection. Pixels
            below this threshold are marked as hotspots.
        - output_path_list (list[str]): List of output file paths for the
            generated GeoTIFF hotspot maps.
        - uint8 (bool, optional): Whether to convert images to uint8 format
            before computation. Default = False.

        Returns:
        - list[str]: Paths to the saved GeoTIFF images containing the binary
            hotspot maps.
        """
        return [
            self.calc_single_image_hotspot_tif(
                file_path, threshold, output_path, uint8
            )
            for file_path, output_path in zip(file_list, output_path_list)
        ]

    def difference(self, a: float, b: float):
        """
        Description:
        Compute the absolute difference between two numbers.

        Args:
        - a (float): The first number.
        - b (float): The second number.

        Returns:
        - diff (float): The absolute difference |a - b|.
        """
        diff = a - b
        return float(abs(diff))

    def division(self, a: float, b: float):
        """
        Description:
        Perform division between two numbers.

        Args:
        - a (float): The divisor (denominator).
        - b (float): The dividend (numerator).

        Returns:
        - result (float): The result of b ÷ a. Returns +inf if a = 0.
        """
        if a == 0:
            return float('inf')
        result = b / a
        return float(result)

    def percentage_change(self, a: float, b: float):
        """
        Description:
        Calculate the percentage change between two numbers, useful for
        comparing relative growth or decline.

        Args:
        - a (float): The original value (denominator).
        - b (float): The new value (numerator).

        Returns:
        - percent (float): The percentage change, computed as
            ((b - a) / a) * 100. Positive values indicate increase,
            negative values indicate decrease. Returns +inf if a = 0.
        """
        if a == 0:
            return float('inf')
        percent = (b - a) / a * 100
        return float(percent)

    def kelvin_to_celsius(self, kelvin: float):
        """
        Description:
        Convert temperature from Kelvin to Celsius.

        Args:
        - kelvin (float): Temperature in Kelvin.

        Returns:
        - celsius (float): Temperature in Celsius, computed as
            (Kelvin - 273.15).
        """
        celsius = kelvin - 273.15
        return celsius

    def celsius_to_kelvin(self, celsius: float):
        """
        Description:
            Convert temperature from Celsius to Kelvin.

        Args:
            celsius (float):
                Temperature in Celsius.

        Returns:
            kelvin (float):
                Temperature in Kelvin, computed as:
                    Kelvin = Celsius + 273.15

        Example:
            >>> celsius_to_kelvin(0)
            273.15
            >>> celsius_to_kelvin(26.85)
            300.0
        """
        kelvin = celsius + 273.15
        return kelvin

    def max_value_and_index(self, x: list):
        """
        Description:
        Find the maximum value in a list and return both the maximum value
        and its index.

        Args:
        - x (list[float]): Input data list.

        Returns:
        - result (tuple[float, int]): A tuple containing:
            * max_value (float): The maximum value in the list.
            * max_index (int): The index of the maximum value.
        """
        import numpy as np

        x_arr = np.asarray(x)
        max_index = np.argmax(x_arr)
        max_value = x_arr[max_index]
        return float(max_value), int(max_index)

    def min_value_and_index(self, x: list):
        """
        Description:
        Find the minimum value in a list and return both the minimum value
        and its index.

        Args:
        - x (list[float]): Input data list.

        Returns:
        - result (tuple[float, int]): A tuple containing:
            * min_value (float): The minimum value in the list.
            * min_index (int): The index of the minimum value.
        """
        import numpy as np

        x_arr = np.asarray(x)
        min_index = np.argmin(x_arr)
        min_value = x_arr[min_index]
        return float(min_value), int(min_index)

    def multiply(self, a, b):
        """
        Description:
            Multiply two numbers and return their product.

        Args:
            a (float or int):
                First number.
            b (float or int):
                Second number.

        Returns:
            result (float or int):
                The product of a and b.

        Example:
            >>> multiply(3, 4)
            12
            >>> multiply(2.5, 4)
            10.0
        """
        return a * b

    def ceil_number(self, n: float):
        """
        Description:
            Return the ceiling (rounded up integer) of a given number.

        Args:
            n (float):
                A numeric value.

        Returns:
            result (int):
                The smallest integer greater than or equal to n.

        Example:
            >>> ceil_number(4.2)
            5
            >>> ceil_number(-3.7)
            -3
        """
        return math.ceil(n)

    def get_list_object_via_indexes(self, input_list, indexes):
        """
        Description:
            Retrieve elements from a list using a list or tuple of indices.

        Args:
            input_list (list):
                The source list from which elements will be extracted.
            indexes (list[int] or tuple[int]):
                A sequence of indices specifying the positions of elements
                to retrieve.

        Returns:
            result (list):
                A list of elements corresponding to the provided indices.

        Example:
            >>> get_list_object_via_indexes(['a', 'b', 'c', 'd'], [1, 3])
            ['b', 'd']
        """
        return [input_list[index] for index in indexes]

    def mean(self, x: list):
        """
        Description:
            Compute the arithmetic mean (average) of a dataset.

        Args:
            x (list[float]):
                Input data array.

        Returns:
            mean_value (float):
                The arithmetic mean of the input values.

        Example:
            >>> mean([1, 2, 3, 4, 5])
            3.0
        """
        import numpy as np

        x_arr = np.asarray(x)
        return float(np.mean(x_arr))

    def calculate_threshold_ratio(
        self,
        image_paths: (str | list[str]),
        threshold: float = 0.75,
        band_index: int = 0,
    ) -> float:
        """
        Description:
            Calculate the average percentage of pixels above a given threshold
            for one or more images and a specified band.

        Args:
            image_paths (str or list[str]):
                Path or list of image file paths.
            threshold (float, optional):
                Threshold value. Default = 0.75.
            band_index (int, optional):
                Band index to use (0-based). Default = 0 (first band).

        Returns:
            percentage (float):
                Average percentage of pixels above the threshold across all
                images.

        Example:
            >>> calculate_threshold_ratio("image1.tif", threshold=0.5)
            42.37
            >>> calculate_threshold_ratio(
            ...     ["img1.tif", "img2.tif"], threshold=0.8, band_index=1
            ... )
            33.12
        """
        import numpy as np

        if isinstance(image_paths, str):
            image_paths = [image_paths]
        ratios = []
        for image_path in image_paths:
            img = self.read_image(image_path)
            if img.ndim == 3:
                if img.shape[0] <= 5 and img.shape[0] < img.shape[-1]:
                    band = img[band_index]
                else:
                    band = img[..., band_index]
            else:
                band = img
            valid_pixels = ~np.isnan(band)
            total_valid_pixels = np.sum(valid_pixels)
            if total_valid_pixels == 0:
                ratios.append(0.0)
                continue
            pixels_above_threshold = np.sum((band > threshold) & valid_pixels)
            percentage = pixels_above_threshold / total_valid_pixels * 100
            ratios.append(float(percentage))
        return float(np.mean(ratios)) if ratios else 0.0

    def calc_single_image_fire_pixels(
        self, file_path: str, fire_threshold: float = 0
    ) -> int:
        """
        Compute the number of fire pixels (MaxFRP > threshold) in an image.

        Args:
            file_path (str): Path to input image.
            fire_threshold (float): Minimum FRP value to be considered as fire
                (default: 0).

        Returns:
            fire_pixels (int): Number of fire pixels
        """
        import numpy as np

        img = self.read_image(file_path)
        if img.size == 0:
            raise ValueError('Input image is empty')
        fire_pixels = np.sum(img > fire_threshold)
        return int(fire_pixels)

    def calc_batch_fire_pixels(
        self, file_list: list[str], fire_threshold: float = 0
    ) -> list[int]:
        """
        Description:
            Compute the number of fire pixels (FRP > threshold) for a batch of
            images.

        Args:
            file_list (list[str]):
                Paths to input images.
            fire_threshold (float, optional):
                Minimum FRP value to be considered as fire. Default = 0.

        Returns:
            fire_pixels (list[int]):
                A list of fire pixel counts, one per input image.

        Example:
            >>> calc_batch_fire_pixels(
            ...     ["img1.tif", "img2.tif"], fire_threshold=50
            ... )
            [123, 89]
        """
        return [
            self.calc_single_image_fire_pixels(file_path, fire_threshold)
            for file_path in file_list
        ]

    def create_fire_increase_map(
        self, change_image_path: str, output_path: str, threshold: float = 20.0
    ) -> str:
        """
        Description:
            Create a binary map highlighting areas where fire increase exceeds
            a specified threshold.

        Args:
            change_image_path (str):
                Path to the fire change image.
            output_path (str):
                Relative path for the output raster file
                (e.g., "question17/hotspot_2022-01-16.tif").
            threshold (float, optional):
                Threshold value in MW. Default = 20.0.

        Returns:
            result (str):
                Path to the saved GeoTIFF fire increase map.

        Example:
            >>> create_fire_increase_map(
            ...     "fire_change.tif", "output/fire_increase.tif",
            ...     threshold=25.0
            ... )
            'Result save at /tmp/output/fire_increase.tif'
        """
        import numpy as np
        import rasterio

        change_img = self.read_image(change_image_path)
        fire_increase_map = (change_img >= threshold).astype(np.uint8)
        with rasterio.open(change_image_path) as src:
            profile = src.profile
            profile.update(dtype=rasterio.uint8, compress='lzw', nodata=255)
            os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
            with rasterio.open(TEMP_DIR / output_path, 'w', **profile) as dst:
                dst.write(fire_increase_map, 1)
        return f'Result save at {TEMP_DIR / output_path}'

    def identify_fire_prone_areas(
        self,
        file_path: str,
        output_path: str,
        threshold_percentile: float = 75,
        uint8: bool = False,
    ) -> tuple[str, float]:
        """
        Description:
            Identify fire-prone areas from a hotspot map based on a given
            percentile threshold.

        Args:
            file_path (str):
                Path to the input hotspot map file.
            output_path (str):
                Relative path for the output raster file
                (e.g., "question17/hotspot_2022-01-16.tif").
            threshold_percentile (float, optional):
                Percentile threshold for identifying fire-prone areas.
                Default = 75.
            uint8 (bool, optional):
                Whether to use uint8 format when reading the input.
                Default = False.

        Returns:
            result (tuple[str, float]):
                A tuple containing:
                - Path to the saved GeoTIFF file with fire-prone areas.
                - Threshold value used for classification.

        Example:
            >>> identify_fire_prone_areas(
            ...     "hotspot_map.tif", "output/fire_prone.tif", 80
            ... )
            ('Result save at /tmp/output/fire_prone.tif', 123.45)
        """
        import numpy as np
        import rasterio

        if uint8:
            hotspot_map = self.read_image_uint8(file_path)
        else:
            hotspot_map = self.read_image(file_path)
        if hotspot_map.size == 0:
            raise ValueError('Input hotspot map is empty')
        valid_pixels = hotspot_map[hotspot_map > 0]
        if len(valid_pixels) == 0:
            threshold_value = 0.0
            fire_prone_areas = np.zeros_like(hotspot_map, dtype=np.uint8)
        else:
            threshold_value = np.percentile(valid_pixels, threshold_percentile)
            fire_prone_areas = (hotspot_map >= threshold_value).astype(
                np.uint8
            )
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(file_path) as src:
            output_profile = src.profile.copy()
            output_profile.update(
                dtype=rasterio.uint8, compress='lzw', nodata=255
            )
            with rasterio.open(
                TEMP_DIR / output_path, 'w', **output_profile
            ) as dst:
                dst.write(fire_prone_areas, 1)
        return f'Result save at {TEMP_DIR / output_path}', float(
            threshold_value
        )

    def get_percentile_value_from_image(self, image_path, percentile):
        """
        Description:
            Calculate the N-th percentile value of pixel values in a raster
            image, and return it as a native Python type matching the image's
            data type.

        Args:
            image_path (str):
                Path to the input raster (.tif) file.
            percentile (int or float):
                Percentile to calculate (range 1-100).

        Returns:
            value (int or float):
                The pixel value corresponding to the specified percentile,
                cast to the appropriate native Python type (int for integer
                rasters, float for floating-point rasters).

        Example:
            >>> get_percentile_value_from_image("fire_map.tif", 90)
            235
        """
        import numpy as np
        import rasterio

        if not 1 <= percentile <= 100:
            raise ValueError('Percentile must be between 1 and 100.')
        with rasterio.open(image_path) as src:
            image = src.read(1)
            dtype = image.dtype
            image = image.astype(np.float32)
        image = image[np.isfinite(image)]
        if image.size == 0:
            raise ValueError('No valid pixel values found in the image.')
        result = np.percentile(image, percentile)
        if np.issubdtype(dtype, np.integer):
            return int(round(result))
        elif np.issubdtype(dtype, np.floating):
            return float(result)
        else:
            raise TypeError(f'Unsupported raster data type: {dtype}')

    def image_division_mean(
        self, image_path1, image_path2=None, band1=1, band2=2
    ):
        """
        Description:
            Calculate the mean of pixel-wise division between two images
            or between two bands of the same image.

        Args:
            image_path1 (str):
                Path to the first image (or the only image if comparing two
                bands).
            image_path2 (str, optional):
                Path to the second image. If None, band1 and band2 of
                image_path1 will be used.
            band1 (int, optional):
                Band index for numerator when using a multi-band image.
                Default = 1.
            band2 (int, optional):
                Band index for denominator when using a multi-band image.
                Default = 2.

        Returns:
            result (float):
                The mean of the valid pixel-wise division results.

        Example:
            >>> image_division_mean("multiband_image.tif", band1=3, band2=2)
            1.245

            >>> image_division_mean("image1.tif", "image2.tif")
            0.876
        """
        import numpy as np
        import rasterio

        if image_path2 is None:
            with rasterio.open(image_path1) as src:
                array1 = src.read(band1).astype(np.float32)
                array2 = src.read(band2).astype(np.float32)
        else:
            with (
                rasterio.open(image_path1) as src1,
                rasterio.open(image_path2) as src2,
            ):
                array1 = src1.read(1).astype(np.float32)
                array2 = src2.read(1).astype(np.float32)
        mask = (array2 != 0) & ~np.isnan(array1) & ~np.isnan(array2)
        ratio = np.full_like(array1, np.nan, dtype=np.float32)
        ratio[mask] = array1[mask] / array2[mask]
        return float(np.nanmean(ratio))

    def calculate_intersection_percentage(
        self, path1, threshold1, path2, threshold2
    ):
        """
        Description:
            Calculate the percentage of pixels that simultaneously satisfy
            threshold conditions in two raster images.

        Args:
            path1 (str):
                Path to the first raster image (e.g., NDVI).
            threshold1 (float):
                Threshold value for the first image (e.g., NDVI > 0.3).
            path2 (str):
                Path to the second raster image (e.g., TVDI).
            threshold2 (float):
                Threshold value for the second image (e.g., TVDI > 0.7).

        Returns:
            percentage (float):
                Percentage of pixels that satisfy both conditions
                over the total valid pixels.

        Example:
            >>> calculate_intersection_percentage(
            ...     "ndvi.tif", 0.3, "tvdi.tif", 0.7
            ... )
            12.54
        """
        import numpy as np
        import rasterio

        with rasterio.open(path1) as src1:
            data1 = src1.read(1).astype(np.float32)
            mask1 = src1.read_masks(1) > 0
        with rasterio.open(path2) as src2:
            data2 = src2.read(1).astype(np.float32)
            mask2 = src2.read_masks(1) > 0
        valid_mask = mask1 & mask2
        valid_data1 = np.where(valid_mask, data1, np.nan)
        valid_data2 = np.where(valid_mask, data2, np.nan)
        condition1 = valid_data1 > threshold1
        condition2 = valid_data2 > threshold2
        intersection_mask = condition1 & condition2
        total_valid_pixels = np.count_nonzero(
            ~np.isnan(valid_data1) & ~np.isnan(valid_data2)
        )
        intersection_pixels = np.count_nonzero(intersection_mask)
        if total_valid_pixels == 0:
            return 0.0
        percentage = intersection_pixels / total_valid_pixels * 100
        return percentage

    def calc_batch_image_mean_mean(
        self, file_list: list[str], uint8: bool = False
    ) -> float:
        """
        Description:
            Compute the average of mean pixel values across a batch of images.

        Args:
            file_list (list[str]):
                List of image file paths.
            uint8 (bool, optional):
                Whether to convert images to uint8 format (0-255).
                Default = False.

        Returns:
            mean_of_means (float):
                The average of the mean pixel values across all images.

        Example:
            >>> calc_batch_image_mean_mean(["img1.tif", "img2.tif"])
            105.67
        """
        import numpy as np

        means = [
            float(self.calc_single_image_mean(file_path, uint8))
            for file_path in file_list
        ]
        return float(np.mean(means))

    def calc_batch_image_mean_max(
        self, file_list: list[str], uint8: bool = False
    ) -> float:
        """
        Description:
            Compute the mean pixel values of a batch of images and return the
            maximum mean.

        Args:
            file_list (list[str]):
                Paths to input images.
            uint8 (bool, optional):
                Whether to treat image as uint8 (0-255 normalization).
                Default = False.

        Returns:
            max_mean (float):
                The maximum mean pixel value among all images.

        Example:
            >>> calc_batch_image_mean_max(["img1.tif", "img2.tif"])
            145.32
        """
        means = [
            float(self.calc_single_image_mean(file_path, uint8))
            for file_path in file_list
        ]
        return max(means)

    def calc_batch_image_mean_max_min(
        self, file_list: list[str], uint8: bool = False
    ) -> tuple[float, float, float]:
        """
        Description:
            Compute the batch-wise statistics across multiple images,
            including:
            - Mean of mean values
            - Maximum of maximum values
            - Minimum of minimum values

        Args:
            file_list (list[str]):
                List of image file paths.
            uint8 (bool, optional):
                Whether to convert the data to uint8 range (0-255).
                Default = False.

        Returns:
            result (tuple[float, float, float]):
                A tuple containing:
                (mean of means, max of maxs, min of mins)

        Example:
            >>> calc_batch_image_mean_max_min(["img1.tif", "img2.tif"])
            (110.5, 243.0, 5.0)
        """
        import numpy as np
        import rasterio

        means = []
        maxs = []
        mins = []
        for file_path in file_list:
            with rasterio.open(file_path) as src:
                img = src.read(1).astype(np.float32)
                img = img[np.isfinite(img)]
                if uint8:
                    img = np.clip(img, 0, 1) * 255
                means.append(np.mean(img))
                maxs.append(np.max(img))
                mins.append(np.min(img))
        return float(np.mean(means)), float(np.max(maxs)), float(np.min(mins))

    def calc_batch_image_mean_threshold(
        self,
        file_list: list[str],
        threshold: float,
        above: bool = True,
        uint8: bool = False,
        band_index: int = 0,
        return_type: str = 'ratio',
    ) -> float | int:
        """
        Description:
            Calculate the percentage or count of images whose mean pixel values
            (in a specified band) are above or below a given threshold.

        Args:
            file_list (list[str]):
                List of image file paths.
            threshold (float):
                Threshold value for comparison.
            above (bool, optional):
                If True, count images with mean > threshold; if False,
                mean < threshold. Default = True.
            uint8 (bool, optional):
                If True, rescale image data to 0-255 range. Default = False.
            band_index (int, optional):
                Index of the band to read (0-based). Default = 0.
            return_type (str, optional):
                - "ratio": return percentage (float, 0-100).
                - "count": return number of images (int).
                Default = "ratio".

        Returns:
            float | int:
                Percentage (0-100) or count of images satisfying the condition.

        Example:
            >>> calc_batch_image_mean_threshold(
            ...     ["img1.tif", "img2.tif"], threshold=100, above=True
            ... )
            50.0
        """
        import numpy as np
        import rasterio

        valid_means = []
        for file_path in file_list:
            try:
                with rasterio.open(file_path) as src:
                    if band_index >= src.count:
                        logger.info(
                            f'Warning: {file_path} does not contain '
                            f'band {band_index + 1}. Skipped.'
                        )
                        continue
                    data = src.read(band_index + 1).astype(np.float32)
                    data = np.where(data == src.nodata, np.nan, data)
                    if uint8:
                        dmin, dmax = np.nanmin(data), np.nanmax(data)
                        if dmax > dmin:
                            data = (data - dmin) / (dmax - dmin) * 255
                        else:
                            data[:] = 0
                    mean_val = np.nanmean(data)
                    if not np.isnan(mean_val):
                        valid_means.append(mean_val)
            except Exception as e:
                logger.info(f'Error processing {file_path}: {e}')
                continue
        if not valid_means:
            return 0 if return_type == 'count' else 0.0
        valid_means_arr = np.array(valid_means)
        if above:
            count = np.sum(valid_means_arr > threshold)
        else:
            count = np.sum(valid_means_arr < threshold)
        if return_type == 'count':
            return int(count)
        elif return_type == 'ratio':
            return float(count / len(valid_means_arr) * 100.0)
        else:
            raise ValueError("return_type must be 'ratio' or 'count'")

    def calculate_multi_band_threshold_ratio(
        self, image_path: str, band_conditions: list
    ) -> float:
        """
        Description:
            Calculate the percentage of pixels that simultaneously satisfy
            multiple band threshold conditions.

        Args:
            image_path (str):
                Path to the multi-band image file.
            band_conditions (list[tuple[int, float, str]]):
                A list of conditions in the form
                (band_index, threshold_value, compare_type):
                    - band_index (int): Zero-based band index.
                    - threshold_value (float): Threshold to apply.
                    - compare_type (str): "above" or "below".

        Returns:
            float:
                Percentage of pixels satisfying all conditions (intersection).

        Example:
            >>> calculate_multi_band_threshold_ratio(
            ...     "multi_band_image.tif",
            ...     [(0, 0.3, "above"), (1, 0.7, "below")]
            ... )
            42.5
        """
        import numpy as np
        import rasterio

        with rasterio.open(image_path) as src:
            bands = []
            for band_index, _, _ in band_conditions:
                band = src.read(band_index + 1).astype(np.float32)
                band[band == src.nodata] = np.nan
                bands.append(band)
        combined_mask = np.ones_like(bands[0], dtype=bool)
        for band, (_, threshold, compare_type) in zip(bands, band_conditions):
            valid = ~np.isnan(band)
            if compare_type.lower() == 'above':
                mask = (band > threshold) & valid
            elif compare_type.lower() == 'below':
                mask = (band < threshold) & valid
            else:
                raise ValueError(
                    f"Invalid compare_type '{compare_type}', "
                    "must be 'above' or 'below'"
                )
            combined_mask &= mask
        total_valid_pixels = float(np.sum(~np.isnan(bands[0])))
        satisfying_pixels = float(np.sum(combined_mask))
        if total_valid_pixels == 0:
            return 0.0
        else:
            return satisfying_pixels / total_valid_pixels * 100

    def count_pixels_satisfying_conditions(
        self, image_path: str, band_conditions: list
    ) -> int:
        """
        Description:
            Count the number of pixels that simultaneously satisfy multiple
            band threshold conditions.

        Args:
            image_path (str):
                Path to the multi-band image file.
            band_conditions (list[tuple[int, float, str]]):
                A list of conditions in the form
                (band_index, threshold_value, compare_type):
                    - band_index (int): Zero-based band index.
                    - threshold_value (float): Threshold to apply.
                    - compare_type (str): "above" or "below".

        Returns:
            int:
                Number of pixels satisfying all threshold conditions
                (intersection).

        Example:
            >>> count_pixels_satisfying_conditions(
            ...     "multi_band_image.tif",
            ...     [(0, 0.3, "above"), (1, 0.7, "below")]
            ... )
            1250
        """
        import numpy as np
        import rasterio

        with rasterio.open(image_path) as src:
            bands = []
            for band_index, _, _ in band_conditions:
                band = src.read(band_index + 1).astype(np.float32)
                nodata = src.nodata
                if nodata is not None:
                    band[band == nodata] = np.nan
                bands.append(band)
        combined_mask = np.ones_like(bands[0], dtype=bool)
        for band, (_, threshold, compare_type) in zip(bands, band_conditions):
            valid = ~np.isnan(band)
            if compare_type.lower() == 'above':
                mask = (band > threshold) & valid
            elif compare_type.lower() == 'below':
                mask = (band < threshold) & valid
            else:
                raise ValueError(
                    f"Invalid compare_type '{compare_type}', "
                    "must be 'above' or 'below'"
                )
            combined_mask &= mask
        return int(np.sum(combined_mask))

    def count_images_exceeding_threshold_ratio(
        self,
        image_paths: (str | list[str]),
        value_threshold: float = 0.7,
        ratio_threshold: float = 20.0,
        mode: str = 'above',
        verbose: bool = True,
    ) -> int:
        """
        Count how many images have a percentage of pixels above or below a
        threshold that exceeds a specified ratio.

        Args:
            image_paths (str or list): Path(s) to image file(s).
            value_threshold (float): Pixel value threshold (e.g., NDVI > 0.7).
            ratio_threshold (float): Percentage threshold for comparison
                (e.g., 20.0 means 20%).
            mode (str):
                - 'above': pixels > value_threshold
                - 'below': pixels < value_threshold
                Default is 'above'.
            verbose (bool): If True, logger.infos detailed ratio results per
                image.

        Returns:
            int: Number of images whose pixel ratio exceeds the
                ratio_threshold.

        Example:
            >>> count_images_exceeding_threshold_ratio(
            ...     ["ndvi_1.tif", "ndvi_2.tif"],
            ...     value_threshold=0.3,
            ...     ratio_threshold=15.0,
            ...     mode="above"
            ... )
            1
        """
        import numpy as np
        import rasterio

        if isinstance(image_paths, str):
            image_paths = [image_paths]
        count_exceeding = 0
        for path in image_paths:
            with rasterio.open(path) as src:
                band = src.read(1).astype(np.float32)
                nodata = src.nodata
                if nodata is not None:
                    band[band == nodata] = np.nan
            valid_mask = ~np.isnan(band)
            total_pixels = np.sum(valid_mask)
            if total_pixels == 0:
                ratio = 0.0
            else:
                if mode == 'below':
                    selected_mask = (band < value_threshold) & valid_mask
                else:
                    selected_mask = (band > value_threshold) & valid_mask
                ratio = np.sum(selected_mask) / total_pixels * 100
            if ratio > ratio_threshold:
                count_exceeding += 1
                status = 'right'
            else:
                status = 'wrong'
            if verbose:
                op = '<' if mode == 'below' else '>'
                logger.info(
                    f"{path}: {ratio:.2f}% {op} {value_threshold} -> "
                    f"{status} (threshold: {ratio_threshold}%)"
                )
        if verbose:
            logger.info(
                f"\nTotal images exceeding threshold ratio: "
                f"{count_exceeding} / {len(image_paths)}"
            )
        return count_exceeding

    def average_ratio_exceeding_threshold(
        self,
        image_paths: (str | list[str]),
        value_threshold: float = 0.7,
        ratio_threshold: float = 20.0,
        mode: str = 'above',
        verbose: bool = True,
    ) -> float:
        """
        Calculate the average percentage of pixels exceeding a value threshold,
        considering only images where the ratio is greater than a specified
        ratio threshold.

        Args:
            image_paths (str or list):
                Path(s) to image file(s).
            value_threshold (float):
                Pixel value threshold (e.g., NDVI > 0.7).
            ratio_threshold (float):
                Minimum percentage threshold for inclusion
                (e.g., 20.0 means 20%).
            mode (str):
                - 'above': pixels > value_threshold
                - 'below': pixels < value_threshold
                Default is 'above'.
            verbose (bool):
                If True, logger.infos detailed ratio results per image.

        Returns:
            float:
                Average percentage of qualifying images.
                Returns 0.0 if no image meets the criteria.

        Example:
            >>> average_ratio_exceeding_threshold(
            ...     ["ndvi_1.tif", "ndvi_2.tif"],
            ...     value_threshold=0.3,
            ...     ratio_threshold=10.0,
            ...     mode="above"
            ... )
            18.5
        """
        import numpy as np
        import rasterio

        if isinstance(image_paths, str):
            image_paths = [image_paths]
        ratios = []
        for path in image_paths:
            try:
                with rasterio.open(path) as src:
                    band = src.read(1).astype(np.float32)
                    nodata = src.nodata
                    if nodata is not None:
                        band[band == nodata] = np.nan
            except Exception as e:
                if verbose:
                    logger.info(f'Error processing {path}: {e}')
                continue
            valid_mask = ~np.isnan(band)
            total_pixels = np.sum(valid_mask)
            if total_pixels == 0:
                ratio = 0.0
            else:
                if mode == 'below':
                    selected_mask = (band < value_threshold) & valid_mask
                else:
                    selected_mask = (band > value_threshold) & valid_mask
                ratio = np.sum(selected_mask) / total_pixels * 100
            if ratio > ratio_threshold:
                ratios.append(ratio)
                status = 'right'
            else:
                status = 'wrong'
            if verbose:
                op = '<' if mode == 'below' else '>'
                logger.info(
                    f"{path}: {ratio:.2f}% {op} {value_threshold} -> "
                    f"{status} (threshold: {ratio_threshold}%)"
                )
        if ratios:
            avg = float(np.mean(ratios))
        else:
            avg = 0.0
        if verbose:
            logger.info(
                f"\nAverage ratio of qualifying images: {avg:.2f}% "
                f"({len(ratios)} out of {len(image_paths)} images)"
            )
        return avg

    def count_images_exceeding_mean_multiplier(
        self,
        image_paths: (str | list[str]),
        mean_multiplier: float = 1.1,
        mode: str = 'above',
        verbose: bool = True,
    ) -> int:
        """
        Count how many images have a mean pixel value above or below
        a multiple of the overall mean pixel value across all images.

        Args:
            image_paths (str or list):
                Path(s) to image file(s).
            mean_multiplier (float):
                Multiplier applied to the overall mean (e.g., 1.1 means 110%).
            mode (str):
                - 'above': count images with mean > mean_multiplier *
                  overall_mean
                - 'below': count images with mean < mean_multiplier *
                  overall_mean
                Default is 'above'.
            verbose (bool):
                If True, logger.infos detailed mean and threshold comparisons
                per image.

        Returns:
            int:
                Number of images satisfying the condition.

        Example:
            >>> count_images_exceeding_mean_multiplier(
            ...     ["img1.tif", "img2.tif", "img3.tif"],
            ...     mean_multiplier=0.9,
            ...     mode="below"
            ... )
            2
        """
        import numpy as np
        import rasterio

        if isinstance(image_paths, str):
            image_paths = [image_paths]
        image_means = []
        for path in image_paths:
            with rasterio.open(path) as src:
                band = src.read(1).astype(np.float32)
                nodata = src.nodata
                if nodata is not None:
                    band[band == nodata] = np.nan
            image_mean = np.nanmean(band)
            image_means.append(image_mean)
        overall_mean = np.nanmean(image_means)
        threshold = mean_multiplier * overall_mean
        if verbose:
            logger.info(
                f'\nOverall mean across all images: {overall_mean:.4f}'
            )
            logger.info(
                f'Threshold for comparison ({mode}): {threshold:.4f}\n'
            )
        count = 0
        for path, img_mean in zip(image_paths, image_means):
            if mode == 'below':
                condition = img_mean < threshold
                op = '<'
            else:
                condition = img_mean > threshold
                op = '>'
            if condition:
                count += 1
                status = 'right'
            else:
                status = 'wrong'
            if verbose:
                logger.info(
                    f'{path}: mean = {img_mean:.4f} {op} '
                    f'{threshold:.4f} -> {status}'
                )
        if verbose:
            logger.info(
                f'\nTotal images satisfying condition: '
                f'{count} / {len(image_paths)}'
            )
        return count

    def calculate_band_mean_by_condition(
        self,
        image_path: str,
        condition_band_index: int,
        condition_threshold: float,
        condition_mode: str = 'above',
        target_band_index: int = 0,
    ) -> float:
        """
        Calculate the mean value of a target band over pixels where a
        condition band satisfies a threshold.

        Args:
            image_path (str):
                Path to the multi-band raster image.
            condition_band_index (int):
                Zero-based index of the band used for thresholding.
            condition_threshold (float):
                Threshold value to apply on the condition band.
            condition_mode (str, default='above'):
                - 'above': select pixels where condition_band >= threshold
                - 'below': select pixels where condition_band < threshold
            target_band_index (int, default=0):
                Zero-based index of the band for which the mean is calculated.

        Returns:
            float:
                Mean value of the target band over selected pixels.

        Example:
            >>> calculate_band_mean_by_condition(
            ...     "multiband_image.tif",
            ...     condition_band_index=1,
            ...     condition_threshold=0.3,
            ...     condition_mode="above",
            ...     target_band_index=2
            ... )
            0.5471
        """
        import numpy as np
        import rasterio

        with rasterio.open(image_path) as src:
            condition_band = src.read(condition_band_index + 1).astype(
                np.float32
            )
            target_band = src.read(target_band_index + 1).astype(np.float32)
            nodata = src.nodata
            if nodata is not None:
                condition_band[condition_band == nodata] = np.nan
                target_band[target_band == nodata] = np.nan
        if condition_mode == 'below':
            mask = (
                (condition_band < condition_threshold)
                & ~np.isnan(condition_band)
                & ~np.isnan(target_band)
            )
        else:
            mask = (
                (condition_band >= condition_threshold)
                & ~np.isnan(condition_band)
                & ~np.isnan(target_band)
            )
        selected_values = target_band[mask]
        mean_value = np.nanmean(selected_values)
        return float(mean_value)

    def calc_threshold_value_mean(
        self,
        path1: (str | list[str]),
        path2: (str | list[str]),
        threshold: float = 300.0,
    ) -> float:
        """
        Calculate the mean value of corresponding raster pixels in path2
        where the raster values in path1 exceed the given threshold.

        Args:
            path1 (Path or List[Path]): Path(s) to the first set of raster
                files (e.g., LST).
            path2 (Path or List[Path]): Path(s) to the second set of raster
                files (e.g., TVDI).
            threshold (float): Threshold for values in path1 (e.g., LST in
                Kelvin).

        Returns:
            float: Mean value of path2 pixels that meet the threshold
                condition in path1. Returns np.nan if no valid data is found.
        """
        import numpy as np
        import rasterio

        files1 = (
            [Path(path1)]
            if isinstance(path1, (str, Path))
            else [Path(p) for p in path1]
        )
        files2 = (
            [Path(path2)]
            if isinstance(path2, (str, Path))
            else [Path(p) for p in path2]
        )
        pattern = re.compile('\\d{4}_\\d{2}_\\d{2}_\\d{4}')
        dict1 = {}
        for f in files1:
            match = pattern.search(f.name)
            if match:
                dict1[match.group()] = f
        dict2 = {}
        for f in files2:
            match = pattern.search(f.name)
            if match:
                dict2[match.group()] = f
        matched_keys = set(dict1.keys()) & set(dict2.keys())
        if not matched_keys:
            logger.info('No matched file pairs found.')
            return np.nan
        all_vals = []
        for key in sorted(matched_keys):
            file1 = dict1[key]
            file2 = dict2[key]
            with rasterio.open(file1) as ds1, rasterio.open(file2) as ds2:
                data1 = ds1.read(1).astype(np.float32)
                data2 = ds2.read(1).astype(np.float32)
                mask = (
                    (data1 > threshold)
                    & (data1 > 0)
                    & (data2 >= 0)
                    & (data2 <= 1)
                )
                if np.any(mask):
                    all_vals.extend(data2[mask].flatten())
        if not all_vals:
            logger.info('No valid values found for path1 > threshold.')
            return np.nan
        return float(np.mean(all_vals))

    def calculate_tif_average(
        self, file_list: list[str], output_path: str, uint8: bool = False
    ) -> str:
        """
        Calculate average of multiple tif files and save result to same
        directory.

        Args:
            file_list (list[str]): List of tif file paths.
            output_path (str): relative path for the output raster file, e.g.
                "benchmark/data/question17/avg_result.tif"
            uint8 (bool): Convert to uint8 format, default False.

        Returns:
            output_path (str): Full path of output file.
        """
        import numpy as np
        from osgeo import gdal

        output_path_full = TEMP_DIR / output_path
        os.makedirs(output_path_full.parent, exist_ok=True)
        ds = gdal.Open(file_list[0])
        bands = ds.RasterCount
        rows = ds.RasterYSize
        cols = ds.RasterXSize
        geotransform = ds.GetGeoTransform()
        projection = ds.GetProjection()
        if bands == 1:
            first_img = ds.GetRasterBand(1).ReadAsArray()
        else:
            first_img = np.stack(
                [ds.GetRasterBand(i + 1).ReadAsArray() for i in range(bands)],
                axis=0,
            )
            first_img = np.transpose(first_img, (1, 2, 0))
        ds = None
        sum_img = np.zeros_like(first_img, dtype=np.float64)
        count = len(file_list)
        sum_img = sum_img + first_img
        for file_path in file_list[1:]:
            ds = gdal.Open(file_path)
            if bands == 1:
                img = ds.GetRasterBand(1).ReadAsArray()
            else:
                img = np.stack(
                    [
                        ds.GetRasterBand(i + 1).ReadAsArray()
                        for i in range(bands)
                    ],
                    axis=0,
                )
                img = np.transpose(img, (1, 2, 0))
            ds = None
            sum_img = sum_img + img
        avg_img = sum_img / count
        if uint8:
            if len(avg_img.shape) == 2:
                min_val = np.min(avg_img)
                max_val = np.max(avg_img)
                avg_img = (avg_img - min_val) / (max_val - min_val) * 255
                avg_img = avg_img.astype(np.uint8)
            else:
                for band in range(avg_img.shape[2]):
                    band_data = avg_img[:, :, band]
                    min_val = np.min(band_data)
                    max_val = np.max(band_data)
                    band_data = (
                        (band_data - min_val) / (max_val - min_val) * 255
                    )
                    avg_img[:, :, band] = band_data.astype(np.uint8)
        driver = gdal.GetDriverByName('GTiff')
        data_type = gdal.GDT_Byte if uint8 else gdal.GDT_Float32
        if len(avg_img.shape) == 2:
            out_ds = driver.Create(
                str(output_path_full), cols, rows, 1, data_type
            )
            out_ds.SetGeoTransform(geotransform)
            out_ds.SetProjection(projection)
            out_ds.GetRasterBand(1).WriteArray(avg_img)
        else:
            out_ds = driver.Create(
                str(output_path_full), cols, rows, bands, data_type
            )
            out_ds.SetGeoTransform(geotransform)
            out_ds.SetProjection(projection)
            for i in range(bands):
                out_ds.GetRasterBand(i + 1).WriteArray(avg_img[:, :, i])
        out_ds = None
        return f'Result save at {output_path_full}'

    def calculate_tif_difference(
        self,
        image_a_path: str,
        image_b_path: str,
        output_path: str,
        uint8: bool = False,
    ) -> str:
        """
        Calculate difference between two tif files (image_b - image_a) and
        save result.

        Args:
            image_a_path (str): Path to first image (will be subtracted from).
            image_b_path (str): Path to second image (will subtract from).
            output_path (str): relative path for the output raster file, e.g.
                "question17/difference_result.tif"
            uint8 (bool): Convert to uint8 format, default False.

        Returns:
            output_path (str): Full path of output file.
        """
        import numpy as np
        from osgeo import gdal

        output_path_full = TEMP_DIR / output_path
        os.makedirs(output_path_full.parent, exist_ok=True)
        ds_a = gdal.Open(image_a_path)
        if ds_a is None:
            raise RuntimeError(f'Failed to open {image_a_path}')
        bands_a = ds_a.RasterCount
        rows_a = ds_a.RasterYSize
        cols_a = ds_a.RasterXSize
        geotransform = ds_a.GetGeoTransform()
        projection = ds_a.GetProjection()
        if bands_a == 1:
            img_a = ds_a.GetRasterBand(1).ReadAsArray()
        else:
            img_a = np.stack(
                [
                    ds_a.GetRasterBand(i + 1).ReadAsArray()
                    for i in range(bands_a)
                ],
                axis=0,
            )
            img_a = np.transpose(img_a, (1, 2, 0))
        ds_a = None
        ds_b = gdal.Open(image_b_path)
        if ds_b is None:
            raise RuntimeError(f'Failed to open {image_b_path}')
        bands_b = ds_b.RasterCount
        rows_b = ds_b.RasterYSize
        cols_b = ds_b.RasterXSize
        if bands_b == 1:
            img_b = ds_b.GetRasterBand(1).ReadAsArray()
        else:
            img_b = np.stack(
                [
                    ds_b.GetRasterBand(i + 1).ReadAsArray()
                    for i in range(bands_b)
                ],
                axis=0,
            )
            img_b = np.transpose(img_b, (1, 2, 0))
        ds_b = None
        if rows_a != rows_b or cols_a != cols_b or bands_a != bands_b:
            raise ValueError(
                f'Images must have same dimensions. '
                f'Image A: {rows_a}x{cols_a}x{bands_a}, '
                f'Image B: {rows_b}x{cols_b}x{bands_b}'
            )
        diff_img = img_b.astype(np.float64) - img_a.astype(np.float64)
        if uint8:
            if len(diff_img.shape) == 2:
                min_val = np.min(diff_img)
                max_val = np.max(diff_img)
                if max_val > min_val:
                    diff_img = (diff_img - min_val) / (max_val - min_val) * 255
                    diff_img = diff_img.astype(np.uint8)
                else:
                    diff_img = np.zeros_like(diff_img, dtype=np.uint8)
            else:
                for band in range(diff_img.shape[2]):
                    band_data = diff_img[:, :, band]
                    min_val = np.min(band_data)
                    max_val = np.max(band_data)
                    if max_val > min_val:
                        band_data = (
                            (band_data - min_val) / (max_val - min_val) * 255
                        )
                        diff_img[:, :, band] = band_data.astype(np.uint8)
                    else:
                        diff_img[:, :, band] = 0
        driver = gdal.GetDriverByName('GTiff')
        data_type = gdal.GDT_Byte if uint8 else gdal.GDT_Float32
        if len(diff_img.shape) == 2:
            out_ds = driver.Create(
                str(output_path_full), cols_a, rows_a, 1, data_type
            )
            out_ds.SetGeoTransform(geotransform)
            out_ds.SetProjection(projection)
            out_ds.GetRasterBand(1).WriteArray(diff_img)
        else:
            out_ds = driver.Create(
                str(output_path_full), cols_a, rows_a, bands_a, data_type
            )
            out_ds.SetGeoTransform(geotransform)
            out_ds.SetProjection(projection)
            for i in range(bands_a):
                out_ds.GetRasterBand(i + 1).WriteArray(diff_img[:, :, i])
        out_ds = None
        return f'Result save at {output_path_full}'

    def subtract(
        self, img1_path: str, img2_path: str, output_path: str
    ) -> str:
        """
        Subtract two images and save result.

        Args:
            img1_path (str): Path to first image.
            img2_path (str): Path to second image.
            output_path (str): relative path for the output raster file, e.g.
                "question17/difference_result.tif"

        Returns:
            str: Path to output file.
        """
        import numpy as np
        import rasterio

        img1 = self.read_image(img1_path)
        img2 = self.read_image(img2_path)
        result = img1.astype(np.float32) - img2.astype(np.float32)
        output_path_full = TEMP_DIR / output_path
        os.makedirs(output_path_full.parent, exist_ok=True)
        with rasterio.open(img1_path) as src:
            profile = src.profile
            profile.update(dtype=rasterio.float32, compress='lzw')
            with rasterio.open(output_path_full, 'w', **profile) as dst:
                dst.write(result, 1)
        return f'Result save at {output_path_full}'

    def calculate_area(self, input_image_path, gsd):
        """
        Description:
        This function calculates the area of non-zero pixels in the input
        image and returns the result.

        Args:
            input_image_path (str): Path to the input image file (TIFF, PNG,
                JPG, etc.).
            gsd (float): Ground sample distance in meters per pixel, if None,
                the function will return the number of non-zero pixels.
        Returns:
            area (int): The area of non-zero pixels in the input image.
        """
        import numpy as np

        image = self.read_image(input_image_path)
        if gsd is None:
            return float(np.sum(image != 0))
        else:
            return float(np.sum(image != 0) * gsd * gsd)

    def grayscale_to_colormap(
        self,
        image_path: str,
        save_name: str,
        cmap_name: str = 'viridis',
        preserve_geo: bool = False,
    ):
        """
        Apply a colormap to a grayscale image and save as a color image.

        Args:
            image_path (str): Path to input grayscale image (e.g. .tif).
            save_name (str): Filename for save color image (.png, .jpg, or
                .tif).
            cmap_name (str): Name of a matplotlib colormap, e.g. 'viridis',
                'RdBu', etc.
            preserve_geo (bool): If True, preserves georeferencing.
        """
        import cv2
        import matplotlib.cm as cm
        import numpy as np
        from osgeo import gdal

        ds = gdal.Open(image_path)
        if ds is None:
            raise RuntimeError(f'Failed to open image: {image_path}')
        gray = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        gray = np.nan_to_num(gray, nan=0.0)
        norm = (gray - np.min(gray)) / (np.max(gray) - np.min(gray) + 1e-08)
        cmap = cm.get_cmap(cmap_name)
        color_img = cmap(norm)[:, :, :3]
        color_img_uint8 = (color_img * 255).astype(np.uint8)
        save_path = TEMP_DIR / save_name
        if preserve_geo:
            driver = gdal.GetDriverByName('GTiff')
            out_ds = driver.Create(
                str(save_path.with_suffix('.tif')),
                xsize=color_img_uint8.shape[1],
                ysize=color_img_uint8.shape[0],
                bands=3,
                eType=gdal.GDT_Byte,
            )
            for i in range(3):
                out_ds.GetRasterBand(i + 1).WriteArray(
                    color_img_uint8[:, :, i]
                )
            gt = ds.GetGeoTransform()
            prj = ds.GetProjection()
            if gt:
                out_ds.SetGeoTransform(gt)
            if prj:
                out_ds.SetProjection(prj)
            out_ds.FlushCache()
            out_ds = None
            ds = None
        else:
            ds = None
            bgr_img = cv2.cvtColor(color_img_uint8, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(save_path), bgr_img)
        return f'Result save at {save_path}'

    def get_filelist(self, dir_path: str):
        """
        Returns a list of files in the specified directory.

        Args:
            dir_path (str): Path to the directory.

        Returns:
            list: List of file names in the directory.
        """
        return sorted(
            [_ for _ in os.listdir(dir_path) if not _.startswith('.')]
        )

    def radiometric_correction_sr(self, input_band_path, output_path):
        """
        Apply Landsat 8 surface reflectance (SR_B*) radiometric correction.

        Args:
            input_band_path (str): Path to the input reflectance band file.
            output_path (str): relative path for the output raster file, e.g.
                "question17/radiometric_correction_2022-01-16.tif"

        Returns:
            str: Path to the saved corrected reflectance file.
        """
        import numpy as np
        import rasterio

        with rasterio.open(input_band_path) as band_src:
            band_array = band_src.read(1)
            band_profile = band_src.profile
        band_array = np.array(band_array, dtype=np.float32)
        corrected_band = band_array * 2.75e-05 + -0.2
        corrected_profile = band_profile.copy()
        corrected_profile.update(dtype=rasterio.float32, nodata=np.nan)
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(
            TEMP_DIR / output_path, 'w', **corrected_profile
        ) as dst:
            dst.write(corrected_band.astype(rasterio.float32), 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def apply_cloud_mask(self, sr_band_path, qa_pixel_path, output_path):
        """
        Apply cloud/shadow mask to a single Landsat 8 surface reflectance band
        using QA_PIXEL band.

        Args:
            sr_band_path (str): Path to surface reflectance band (e.g., SR_B3
                or SR_B5).
            qa_pixel_path (str): Path to QA_PIXEL band.
            output_path (str): relative path for the output raster file, e.g.
                "question17/cloud_mask_2022-01-16.tif"

        Returns:
            str: Path to the saved masked raster file.
        """
        import numpy as np
        import rasterio

        cloud_mask_bits = 1 + 2 + 4 + 8 + 16
        os.makedirs((TEMP_DIR / output_path).parent, exist_ok=True)
        with rasterio.open(sr_band_path) as band_src:
            band = band_src.read(1).astype(np.float32)
            profile = band_src.profile
        with rasterio.open(qa_pixel_path) as qa_src:
            qa = qa_src.read(1)
        mask = qa & cloud_mask_bits == 0
        band[~mask] = np.nan
        output_profile = profile.copy()
        output_profile.update(dtype=rasterio.float32, nodata=np.nan)
        with rasterio.open(
            TEMP_DIR / output_path, 'w', **output_profile
        ) as dst:
            dst.write(band.astype(rasterio.float32), 1)
        return f'Result saved at {TEMP_DIR / output_path}'

    def read_image(self, file_path: str) -> Any:
        import numpy as np
        from osgeo import gdal

        ds = gdal.Open(file_path)
        if ds is None:
            raise RuntimeError(f'Failed to open {file_path}')
        bands = ds.RasterCount
        if bands == 1:
            img = ds.GetRasterBand(1).ReadAsArray()
        else:
            img = np.stack(
                [ds.GetRasterBand(i + 1).ReadAsArray() for i in range(bands)],
                axis=0,
            )
            img = np.transpose(img, (1, 2, 0))
        ds = None
        return img

    def read_image_uint8(self, file_path: str) -> Any:
        import numpy as np
        from osgeo import gdal

        ds = gdal.Open(file_path)
        if ds is None:
            raise RuntimeError(f'Failed to open {file_path}')
        bands = ds.RasterCount
        if bands == 1:
            img = ds.GetRasterBand(1).ReadAsArray()
        else:
            img = np.stack(
                [ds.GetRasterBand(i + 1).ReadAsArray() for i in range(bands)],
                axis=0,
            )
            img = np.transpose(img, (1, 2, 0))
        ds = None
        img = img.astype(np.float32)
        min_val = np.min(img)
        max_val = np.max(img)
        if max_val > min_val:
            img = (img - min_val) / (max_val - min_val) * 255
        else:
            img = np.zeros_like(img)
        return img.astype(np.uint8)

    def get_geotransform(self, file_path) -> tuple:
        from osgeo import gdal

        ds = gdal.Open(file_path)
        if ds is None:
            raise RuntimeError(f'Failed to open {file_path}')
        geo = ds.GetGeoTransform()
        proj = ds.GetProjection()
        ds = None
        if geo == (0, 1.0, 0, 0, 0, 1.0):
            return None, None
        else:
            return geo, proj

    def get_tools(self) -> List[FunctionTool]:
        """Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.calculate_batch_ndvi),
            FunctionTool(self.calculate_batch_ndwi),
            FunctionTool(self.calculate_batch_ndbi),
            FunctionTool(self.calculate_batch_evi),
            FunctionTool(self.calculate_batch_nbr),
            FunctionTool(self.calculate_batch_fvc),
            FunctionTool(self.calculate_batch_wri),
            FunctionTool(self.calculate_batch_ndti),
            FunctionTool(self.calculate_batch_frp),
            FunctionTool(self.calculate_batch_ndsi),
            FunctionTool(
                self.calc_extreme_snow_loss_percentage_from_binary_map
            ),
            FunctionTool(self.compute_tvdi),
            FunctionTool(self.band_ratio),
            FunctionTool(self.lst_single_channel),
            FunctionTool(self.lst_multi_channel),
            FunctionTool(self.split_window),
            FunctionTool(self.temperature_emissivity_separation),
            FunctionTool(self.modis_day_night_lst),
            FunctionTool(self.ttm_lst),
            FunctionTool(self.calculate_mean_lst_by_ndvi),
            FunctionTool(self.calculate_max_lst_by_ndvi),
            FunctionTool(self.calculate_ATI),
            FunctionTool(self.dual_polarization_differential),
            FunctionTool(self.dual_frequency_diff),
            FunctionTool(self.multi_freq_bt),
            FunctionTool(self.chang_single_param_inversion),
            FunctionTool(self.nasa_team_sea_ice_concentration),
            FunctionTool(self.dual_polarization_ratio),
            FunctionTool(self.calculate_water_turbidity_ntu),
            FunctionTool(self.coefficient_of_variation),
            FunctionTool(self.skewness),
            FunctionTool(self.kurtosis),
            FunctionTool(self.calc_batch_image_mean),
            FunctionTool(self.calc_batch_image_std),
            FunctionTool(self.calc_batch_image_median),
            FunctionTool(self.calc_batch_image_min),
            FunctionTool(self.calc_batch_image_max),
            FunctionTool(self.calc_batch_image_skewness),
            FunctionTool(self.calc_batch_image_kurtosis),
            FunctionTool(self.calc_batch_image_sum),
            FunctionTool(self.calc_batch_image_hotspot_percentage),
            FunctionTool(self.calc_batch_image_hotspot_tif),
            FunctionTool(self.difference),
            FunctionTool(self.division),
            FunctionTool(self.percentage_change),
            FunctionTool(self.kelvin_to_celsius),
            FunctionTool(self.celsius_to_kelvin),
            FunctionTool(self.max_value_and_index),
            FunctionTool(self.min_value_and_index),
            FunctionTool(self.multiply),
            FunctionTool(self.ceil_number),
            FunctionTool(self.get_list_object_via_indexes),
            FunctionTool(self.mean),
            FunctionTool(self.calculate_threshold_ratio),
            FunctionTool(self.calc_batch_fire_pixels),
            FunctionTool(self.create_fire_increase_map),
            FunctionTool(self.identify_fire_prone_areas),
            FunctionTool(self.get_percentile_value_from_image),
            FunctionTool(self.image_division_mean),
            FunctionTool(self.calculate_intersection_percentage),
            FunctionTool(self.calc_batch_image_mean_mean),
            FunctionTool(self.calc_batch_image_mean_max),
            FunctionTool(self.calc_batch_image_mean_max_min),
            FunctionTool(self.calc_batch_image_mean_threshold),
            FunctionTool(self.calculate_multi_band_threshold_ratio),
            FunctionTool(self.count_pixels_satisfying_conditions),
            FunctionTool(self.count_images_exceeding_threshold_ratio),
            FunctionTool(self.average_ratio_exceeding_threshold),
            FunctionTool(self.count_images_exceeding_mean_multiplier),
            FunctionTool(self.calculate_band_mean_by_condition),
            FunctionTool(self.calc_threshold_value_mean),
            FunctionTool(self.calculate_tif_average),
            FunctionTool(self.calculate_tif_difference),
            FunctionTool(self.subtract),
            FunctionTool(self.calculate_area),
            FunctionTool(self.grayscale_to_colormap),
            FunctionTool(self.get_filelist),
            FunctionTool(self.radiometric_correction_sr),
            FunctionTool(self.apply_cloud_mask),
            FunctionTool(self.compute_linear_trend),
            FunctionTool(self.mann_kendall_test),
            FunctionTool(self.sens_slope),
            FunctionTool(self.stl_decompose),
            FunctionTool(self.detect_change_points),
            FunctionTool(self.autocorrelation_function),
            FunctionTool(self.detect_seasonality_acf),
            FunctionTool(self.getis_ord_gi_star),
            FunctionTool(self.analyze_hotspot_direction),
            FunctionTool(self.count_spikes_from_values),
            FunctionTool(self.threshold_segmentation),
            FunctionTool(self.bbox_expansion),
            FunctionTool(self.count_above_threshold),
            FunctionTool(self.count_skeleton_contours),
            FunctionTool(self.bboxes2centroids),
            FunctionTool(self.centroid_distance_extremes),
            FunctionTool(self.calculate_bbox_area),
        ]
