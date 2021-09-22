import datetime

import numpy as np
from xarray.core.dataarray import DataArray as xarray_da

# Type Hints
from xarray.core.dataset import Dataset as xarray_ds

from .grid import get_buffer_cells, non_nan_cells
from .network import get_all_basin_mouth


def get_empty_da(da_template: xarray_da, da_name: str) -> xarray_da:
    """Get an DataArray of nan of the same shape as another DataArray

    Args:
        da_template (xarray_da): DataArray to use as template
        da_name (str): Name of new DataArray

    Returns:
        xarray_da: DataArray with shape of da_template containing only np.nan
    """
    da = da_template.copy().rename(da_name)
    da.values[:] = np.nan
    return da


def get_basin_mouth_mask(network: xarray_ds) -> xarray_da:
    """From a given rgispy network, generate a mask of all the basin mouth cells

    Args:
        network (xarray DataSet): network with ID DataArray

    Returns:
        xarray DataArray: mask DataArray of basin mouths
    """
    basin_mouths = get_all_basin_mouth(network)

    mask = get_empty_da(network["ID"], "BasinMouth")

    for _, cell_idx in basin_mouths:
        cellid = network["ID"][cell_idx].data.tolist()
        mask[cell_idx] = cellid
    mask = mask.assign_attrs({"description": "Mouth cells of basins", "Type": "Point"})
    return mask


def get_mask_ds(network: xarray_ds) -> xarray_ds:
    """Get a xarray dataset skeleton for setting mask variables to

    Args:
        network (xarray Dataset): xarray Dataset of network

    Returns:
        xarray Dataset: xarray Dataset with appropriate skeleton for given network
    """
    todrop = list(network.data_vars.keys())
    if "spatial_ref" in todrop:
        todrop.remove("spatial_ref")
    if "ID" in todrop:
        todrop.remove("ID")

    mask_ds = network.copy().drop(todrop)
    mask_ds = mask_ds.assign_attrs(
        {
            "How to use stored Attribute Tables": "Import as pandas dataframe using command: pd.read_csv(StringIO(<xArray>.attrs['Attribute Table']),sep='\t')",
            "creation_date": "{}".format(datetime.datetime.now()),
            "crs": "+init=epsg:4326",
        }
    )
    return mask_ds


def _mask_buffer_single(network, buffer, mask, lati, loni):
    def _lookup_cellid(lati, loni):
        cellid = network["ID"][lati, loni].data.tolist()
        return cellid

    lat_max, lon_max = mask.shape
    buffer_cells = get_buffer_cells(lati, loni, buffer, lat_max, lon_max)
    for i, j in buffer_cells:
        cellid = _lookup_cellid(i, j)
        mask[i, j] = cellid

    return mask


def mask_buffer(point_mask_da, network, buffer, mask_name=None):
    da = point_mask_da.copy()
    grid_indexes = non_nan_cells(da.data)
    mask = da.data
    for latlon in grid_indexes:
        mask = _mask_buffer_single(network, buffer, mask, latlon[0], latlon[1])

    da.data = mask

    if mask_name:
        da = da.rename(mask_name)
    else:
        new_name = da.name + "_Buffer{}".format(buffer)
        da = da.rename(new_name)

    new_desc = da.description + " with {} cell buffer".format(buffer)
    da.attrs.update(description=new_desc)
    return da
